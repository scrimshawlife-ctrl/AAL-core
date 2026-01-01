from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .effects_store import EffectStore
from .runtime import ers_record_effects
from .stabilization import StabilizationState
from .tuning_apply import hot_apply_tuning_ir


@dataclass(frozen=True)
class CanaryApplyResult:
    rolled_back: bool
    applied: Dict[str, Any]
    rejected: Dict[str, str]
    rollback_ir: Optional[Dict[str, Any]]
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    drift_metric: Optional[str]
    drift_delta: Optional[float]


def _is_worse(*, before: float, after: float, policy: Dict[str, Any]) -> bool:
    """
    Determine whether drift "worsened" under canary policy.

    For minimization metrics (default), an increase is worse.
    Thresholds:
    - canary_max_abs_delta: absolute worsening allowed (default 0.0)
    - canary_max_rel_delta: relative worsening allowed (default 0.0)
    """
    max_abs = float(policy.get("canary_max_abs_delta", 0.0) or 0.0)
    max_rel = float(policy.get("canary_max_rel_delta", 0.0) or 0.0)
    delta = float(after) - float(before)
    if delta <= max_abs:
        return False
    denom = abs(float(before)) if float(before) != 0.0 else 1.0
    if (delta / denom) <= max_rel:
        return False
    return True


def canary_apply_tuning_ir(
    *,
    tuning_ir: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    capability,
    effects_store: EffectStore,
    get_metrics_snapshot: Callable[[], Dict[str, Any]],
    get_current_assignments: Callable[[str], Dict[str, Any]],
    stab: Optional[StabilizationState] = None,
    cycle_boundary: bool = True,
    policy: Optional[Dict[str, Any]] = None,
) -> CanaryApplyResult:
    """
    Apply tuning IR as a tiny canary and rollback on drift.

    NOTE: This function mutates the dict returned by get_current_assignments(module_id)
    in-place when applying and rolling back. Callers should provide a mutable mapping
    representing the live assignment state for that module.
    """
    policy = policy or {}
    stab = stab or StabilizationState(cycles_since_change={})

    before_metrics = get_metrics_snapshot() or {}
    current = get_current_assignments(str(tuning_ir.get("module_id", "")))
    before_assignments = dict(current or {})

    har = hot_apply_tuning_ir(
        tuning_ir=tuning_ir,
        tuning_envelope=tuning_envelope,
        capability=capability,
        stab=stab,
        cycle_boundary=cycle_boundary,
    )

    # Apply in-place (best-effort).
    mode = str(tuning_ir.get("mode", ""))
    if mode != "shadow_tune":
        for k, v in (har.applied or {}).items():
            current[k] = v

    after_metrics = get_metrics_snapshot() or {}

    # Record observed effects (for each applied knob).
    metric_snapshot = before_metrics
    for knob, val in (har.applied or {}).items():
        ers_record_effects(
            effects_store=effects_store,
            module_id=str(tuning_ir.get("module_id", "")),
            knob=str(knob),
            value=val,
            metrics_snapshot=metric_snapshot,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
        )

    metric_name = (
        str(tuning_ir.get("metric_name"))
        if tuning_ir.get("metric_name") is not None
        else str(policy.get("canary_metric_name", "latency_ms_p95"))
    )
    drift_delta: Optional[float] = None
    worse = False
    if metric_name in before_metrics and metric_name in after_metrics:
        b = before_metrics[metric_name]
        a = after_metrics[metric_name]
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            drift_delta = float(a) - float(b)
            worse = _is_worse(before=float(b), after=float(a), policy=policy)

    if worse and mode != "shadow_tune":
        # Rollback in-place.
        current.clear()
        current.update(before_assignments)
        rollback_ir = {
            "schema_version": "tuning-ir/0.1",
            "mode": "rollback",
            "module_id": str(tuning_ir.get("module_id", "")),
            "assignments": before_assignments,
            "reason_tags": ["canary_rollback"],
        }
        return CanaryApplyResult(
            rolled_back=True,
            applied=har.applied,
            rejected=har.rejected,
            rollback_ir=rollback_ir,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            drift_metric=metric_name,
            drift_delta=drift_delta,
        )

    return CanaryApplyResult(
        rolled_back=False,
        applied=har.applied,
        rejected=har.rejected,
        rollback_ir=None,
        before_metrics=before_metrics,
        after_metrics=after_metrics,
        drift_metric=metric_name,
        drift_delta=drift_delta,
    )

