from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from abx_runes.tuning.hashing import content_hash

from .baseline import compute_baseline_signature
from .drift_sentinel import DriftReport, compute_drift
from .effects_store import EffectStore, record_effect
from .rollback import rollback_to_previous
from .tuning_apply import HotApplyResult, hot_apply_tuning_ir


@dataclass(frozen=True)
class CanaryResult:
    applied: bool
    rolled_back: bool
    rollback_ir: Optional[Dict[str, Any]]
    reason: str
    drift: Optional[Dict[str, Any]] = None


def canary_apply_tuning_ir(
    *,
    tuning_ir: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    capability,
    stabilization_state,
    effects_store: EffectStore,
    get_metrics_snapshot: Callable[[], Dict[str, Dict[str, Any]]],  # returns dict(module_id -> metrics dict)
    get_current_assignments: Callable[[str], Dict[str, Any]],  # returns dict(knob -> value)
    cycle_boundary: bool,
    policy: Dict[str, Any],
    apply_fn: Optional[Callable[..., HotApplyResult]] = None,
) -> CanaryResult:
    """
    Apply a tuning IR as a canary, observe drift for a deterministic number of cycles,
    and rollback if drift worsens beyond explicit, policy-controlled thresholds.
    """
    module_id = str(tuning_ir.get("module_id", ""))
    node_id = str(tuning_ir.get("node_id", ""))
    assigns = dict(tuning_ir.get("assignments") or {})
    if not assigns:
        return CanaryResult(applied=False, rolled_back=False, rollback_ir=None, reason="empty_assignments")

    before = (get_metrics_snapshot() or {}).get(module_id, {}) or {}
    baseline = compute_baseline_signature(before)

    prev_assignments = get_current_assignments(module_id) or {}
    if not prev_assignments:
        # Fallback hook (optional): caller may supply a deterministic cached view.
        cached = (policy.get("prev_assignments_by_module") or {}).get(module_id)
        if isinstance(cached, dict):
            prev_assignments = cached

    fn = hot_apply_tuning_ir if apply_fn is None else apply_fn

    # canary apply
    fn(
        tuning_ir=tuning_ir,
        tuning_envelope=tuning_envelope,
        capability=capability,
        stab=stabilization_state,
        cycle_boundary=cycle_boundary,
    )

    # observe N cycles deterministically
    canary_cycles = int(policy.get("canary_cycles", 2))
    after = before
    for _ in range(max(1, canary_cycles)):
        after = (get_metrics_snapshot() or {}).get(module_id, after) or after

    drift: DriftReport = compute_drift(
        prev_metrics=before,
        now_metrics=after,
        latency_spike_ratio=float(policy.get("rollback_latency_spike_ratio", 1.10)),
        error_spike_ratio=float(policy.get("rollback_error_spike_ratio", 1.20)),
        cost_spike_ratio=float(policy.get("rollback_cost_spike_ratio", 1.10)),
        throughput_drop_ratio=float(policy.get("rollback_throughput_drop_ratio", 0.90)),
        degraded_score_threshold=float(policy.get("rollback_degraded_score_threshold", 0.35)),
    )

    # Always record effects for learning continuity.
    # On rollback we additionally record an explicit penalty metric.
    def _record_for_attempt(*, penalty: bool) -> None:
        for k, v in assigns.items():
            record_effect(
                effects_store,
                module_id=module_id,
                knob=k,
                value=v,
                baseline_signature=baseline,
                before_metrics=before,
                after_metrics=after,
            )
            if penalty:
                record_effect(
                    effects_store,
                    module_id=module_id,
                    knob=k,
                    value=v,
                    baseline_signature=baseline,
                    before_metrics={"rollback_penalty": 0.0},
                    after_metrics={"rollback_penalty": 1.0},
                )

    if drift.degraded_mode:
        rb_res = rollback_to_previous(
            module_id=module_id,
            source_cycle_id=str(tuning_ir.get("source_cycle_id", "")),
            node_id=node_id,
            tuning_envelope=tuning_envelope,
            capability=capability,
            stabilization_state=stabilization_state,
            prev_assignments=prev_assignments,
            revert_keys=assigns,
            cycle_boundary=cycle_boundary,
            apply_fn=apply_fn,
        )

        _record_for_attempt(penalty=True)

        rb = {
            "schema_version": "rollback-ir/0.1",
            "rollback_hash": "",
            "source_cycle_id": str(tuning_ir.get("source_cycle_id", "")),
            "module_id": module_id,
            "baseline_signature": baseline,
            "tuning_ir_hash": str(tuning_ir.get("ir_hash", "")),
            "reason": {
                "degraded_mode": drift.degraded_mode,
                "drift_score": drift.drift_score,
                "reasons": drift.reasons,
            },
            "reverted_assignments": dict(rb_res.attempted),
            "provenance": {
                "before_hash": content_hash(before),
                "after_hash": content_hash(after),
            },
        }
        rb["rollback_hash"] = content_hash(rb, blank_fields=("rollback_hash",))

        # Ledger continuity: append rollback artifact.
        effects_store.artifacts.append(dict(rb))

        return CanaryResult(
            applied=True,
            rolled_back=True,
            rollback_ir=rb,
            reason="rolled_back",
            drift=rb["reason"],
        )

    _record_for_attempt(penalty=False)
    return CanaryResult(applied=True, rolled_back=False, rollback_ir=None, reason="committed", drift=None)

