from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RiskPolicy:
    """
    Deterministic clamp outputs for a tuning cycle.

    Notes:
    - Budgets are enforced in the router over *selected* exploit changes.
    - Per-knob envelopes supply risk_units + expected_latency_bump_ms_p95.
    """

    max_changes_per_cycle: int
    max_total_risk_units: float
    max_latency_bump_ms_p95: float
    allow_explore: bool
    allow_exploit: bool
    do_nothing: bool
    reasons: List[str]


def clamp_policy(
    *,
    base_policy: Dict[str, Any],
    drift_score: float,
    degraded_mode: bool,
) -> RiskPolicy:
    """
    Deterministic policy clamp:
    - if degraded OR drift high: disable explore, clamp exploit changes and budgets
    - if drift extreme: do_nothing
    """
    reasons: List[str] = []

    drift_high = drift_score >= float(base_policy.get("drift_high_threshold", 0.60))
    drift_extreme = drift_score >= float(base_policy.get("drift_extreme_threshold", 0.85))

    if degraded_mode:
        reasons.append("degraded_mode")
    if drift_high:
        reasons.append("drift_high")
    if drift_extreme:
        reasons.append("drift_extreme")

    if drift_extreme or bool(base_policy.get("force_do_nothing", False)):
        return RiskPolicy(
            max_changes_per_cycle=0,
            max_total_risk_units=0.0,
            max_latency_bump_ms_p95=0.0,
            allow_explore=False,
            allow_exploit=False,
            do_nothing=True,
            reasons=reasons or ["do_nothing"],
        )

    if degraded_mode or drift_high:
        return RiskPolicy(
            max_changes_per_cycle=int(base_policy.get("clamped_max_changes_per_cycle", 1)),
            max_total_risk_units=float(base_policy.get("clamped_max_total_risk_units", 0.75)),
            max_latency_bump_ms_p95=float(base_policy.get("clamped_max_latency_bump_ms_p95", 3.0)),
            allow_explore=False,
            allow_exploit=True,
            do_nothing=False,
            reasons=reasons,
        )

    # normal
    return RiskPolicy(
        max_changes_per_cycle=int(base_policy.get("max_changes_per_cycle", 6)),
        max_total_risk_units=float(base_policy.get("max_total_risk_units", 4.0)),
        max_latency_bump_ms_p95=float(base_policy.get("max_latency_bump_ms_p95", 20.0)),
        allow_explore=bool(base_policy.get("enable_explore", True)),
        allow_exploit=True,
        do_nothing=False,
        reasons=reasons,
    )


def clamp_exploit_assignments(
    *,
    assignments: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    risk_policy: RiskPolicy,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Clamp exploit assignments deterministically to low-risk knobs only.

    Enforces, in order:
    - allow_exploit/do_nothing
    - hot_apply required
    - per-knob single limits (risk_units, expected_latency_bump_ms_p95)
    - max_changes_per_cycle
    - total budgets (sum risk_units, sum expected_latency_bump_ms_p95)

    Returns:
        (clamped_assignments, report)
    """
    if risk_policy.do_nothing or (not risk_policy.allow_exploit):
        return {}, {"allowed_knobs": [], "rejected": {k: "exploit_disabled" for k in sorted(assignments.keys())}}

    specs = {str(k.get("name")): (k or {}) for k in (tuning_envelope.get("knobs") or [])}
    out: Dict[str, Any] = {}
    rejected: Dict[str, str] = {}

    total_risk = 0.0
    total_lat = 0.0

    def _f(x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return float(default)
            return float(x)
        except Exception:
            return float(default)

    for name in sorted(assignments.keys()):
        if name not in specs:
            rejected[name] = "unknown_knob"
            continue
        spec = specs[name]

        if not bool(spec.get("hot_apply", False)):
            rejected[name] = "not_hot_apply"
            continue

        ru = _f(spec.get("risk_units"), 0.0)
        lb = _f(spec.get("expected_latency_bump_ms_p95"), 0.0)

        if ru > float(risk_policy.max_total_risk_units):
            rejected[name] = "risk_units_over_budget_single"
            continue
        if lb > float(risk_policy.max_latency_bump_ms_p95):
            rejected[name] = "latency_bump_over_budget_single"
            continue

        if len(out) >= int(risk_policy.max_changes_per_cycle):
            rejected[name] = "max_changes_per_cycle"
            continue

        if (total_risk + ru) > float(risk_policy.max_total_risk_units):
            rejected[name] = "risk_budget_exhausted"
            continue
        if (total_lat + lb) > float(risk_policy.max_latency_bump_ms_p95):
            rejected[name] = "latency_budget_exhausted"
            continue

        out[name] = assignments[name]
        total_risk += ru
        total_lat += lb

    report = {
        "allowed_knobs": sorted(out.keys()),
        "rejected": {k: rejected[k] for k in sorted(rejected.keys())},
        "total_risk_units": float(total_risk),
        "total_expected_latency_bump_ms_p95": float(total_lat),
        "max_changes_per_cycle": int(risk_policy.max_changes_per_cycle),
        "max_total_risk_units": float(risk_policy.max_total_risk_units),
        "max_latency_bump_ms_p95": float(risk_policy.max_latency_bump_ms_p95),
    }
    return out, report

