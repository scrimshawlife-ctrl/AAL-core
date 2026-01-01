from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from abx_runes.tuning.hashing import content_hash

from .baseline import compute_baseline_signature
from .drift_sentinel import compute_drift
from .effects_store import EffectStore, record_effect
from .rollback import rollback_to_previous
from .rollback_ir import RollbackIR
from .tuning_apply import HotApplyResult, hot_apply_tuning_ir


@dataclass(frozen=True)
class CanaryResult:
    applied: bool
    rolled_back: bool
    rollback_ir: Optional[Dict[str, Any]]
    reason: str


def canary_apply_tuning_ir(
    *,
    tuning_ir: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    capability,
    stabilization_state,
    effects_store: EffectStore,
    get_metrics_snapshot: Callable[[], Dict[str, Dict[str, Any]]],
    get_current_assignments: Callable[[str], Dict[str, Any]],
    cycle_boundary: bool,
    policy: Dict[str, Any],
    apply_fn: Callable[..., HotApplyResult] = hot_apply_tuning_ir,
) -> CanaryResult:
    """
    ERS v1.2:
    Apply a tuning IR as a canary, observe drift for a deterministic number of cycles,
    and rollback if drift worsens beyond explicit policy thresholds.

    Negative evidence recording:
    - On rollback, we still record deltas into EffectStore (deltas should be "bad" for
      the relevant metrics), so the optimizer learns "this hurts" under that baseline.
    """
    module_id = str(tuning_ir.get("module_id", ""))
    node_id = str(tuning_ir.get("node_id", ""))
    assigns = dict(tuning_ir.get("assignments") or {})
    if not assigns:
        return CanaryResult(applied=False, rolled_back=False, rollback_ir=None, reason="empty_assignments")

    # baseline snapshot + signature (bucket key)
    before_all = get_metrics_snapshot() or {}
    before = dict((before_all.get(module_id) or {}) or {})
    baseline = compute_baseline_signature(before)

    prev_assignments = dict((get_current_assignments(module_id) or {}) or {})

    # apply canary
    apply_fn(
        tuning_ir=tuning_ir,
        tuning_envelope=tuning_envelope,
        capability=capability,
        stab=stabilization_state,
        cycle_boundary=cycle_boundary,
    )

    # observe N cycles deterministically (simple polling hook for now)
    canary_cycles = int(policy.get("canary_cycles", 2) or 2)
    after = before
    for _ in range(max(1, canary_cycles)):
        snap = get_metrics_snapshot() or {}
        after = dict((snap.get(module_id) or {}) or after)

    drift = compute_drift(
        prev_metrics=before,
        now_metrics=after,
        latency_spike_ratio=float(policy.get("rollback_latency_spike_ratio", 1.10)),
        error_spike_ratio=float(policy.get("rollback_error_spike_ratio", 1.20)),
        cost_spike_ratio=float(policy.get("rollback_cost_spike_ratio", 1.10)),
        throughput_drop_ratio=float(policy.get("rollback_throughput_drop_ratio", 0.90)),
        degraded_score_threshold=float(policy.get("rollback_degraded_score_threshold", 0.35)),
    )

    def _record_all_effects() -> None:
        for k, v in assigns.items():
            record_effect(
                effects_store,
                module_id=module_id,
                knob=str(k),
                value=v,
                baseline_signature=baseline,
                before_metrics=before,
                after_metrics=after,
            )

    if drift.degraded_mode:
        # rollback: revert each changed knob to prior value if known
        reverted: Dict[str, Any] = {}
        for k in assigns.keys():
            if k in prev_assignments:
                reverted[k] = prev_assignments[k]

        if reverted:
            rollback_to_previous(
                source_cycle_id=str(tuning_ir.get("source_cycle_id", "")),
                module_id=module_id,
                node_id=node_id,
                reverted_assignments=reverted,
                tuning_envelope=tuning_envelope,
                capability=capability,
                stabilization_state=stabilization_state,
                cycle_boundary=cycle_boundary,
                reason_tags=["rollback_v1.2"],
            )

        # record negative evidence (deltas) for the attempted value
        _record_all_effects()

        rb = RollbackIR(
            schema_version="rollback-ir/0.1",
            rollback_hash="",
            source_cycle_id=str(tuning_ir.get("source_cycle_id", "")),
            module_id=module_id,
            baseline_signature=baseline,
            tuning_ir_hash=str(tuning_ir.get("ir_hash", "")),
            reason=dict(drift.__dict__),
            reverted_assignments=dict(reverted),
            provenance={
                "before_hash": content_hash(before),
                "after_hash": content_hash(after),
            },
        ).to_dict()
        rb["rollback_hash"] = content_hash({**rb, "rollback_hash": ""})
        return CanaryResult(applied=True, rolled_back=True, rollback_ir=rb, reason="rolled_back")

    # success: record effects as usual (learning continues)
    _record_all_effects()
    return CanaryResult(applied=True, rolled_back=False, rollback_ir=None, reason="committed")

