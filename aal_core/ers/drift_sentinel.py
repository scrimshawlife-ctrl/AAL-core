from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DriftReport:
    """
    Deterministic drift evaluation between two metric snapshots.

    degraded_score is in [0, 1] and represents the fraction of checked metrics
    that violated rollback thresholds.
    """

    degraded_mode: bool
    degraded_score: float
    checks: Dict[str, Dict[str, Any]]


def _ratio(now: float, prev: float) -> Optional[float]:
    if prev == 0:
        return None
    return float(now) / float(prev)


def compute_drift(
    *,
    prev_metrics: Dict[str, Any],
    now_metrics: Dict[str, Any],
    latency_spike_ratio: float = 1.10,
    error_spike_ratio: float = 1.20,
    cost_spike_ratio: float = 1.10,
    throughput_drop_ratio: float = 0.90,
    degraded_score_threshold: float = 0.35,
) -> DriftReport:
    """
    Explicit, policy-controlled rollback thresholds.

    Expected metrics (if present):
    - latency_ms_p95: higher is worse (rollback if now/prev > latency_spike_ratio)
    - error_rate:     higher is worse (rollback if now/prev > error_spike_ratio)
    - cost_units:     higher is worse (rollback if now/prev > cost_spike_ratio)
    - throughput_per_s: lower is worse (rollback if now/prev < throughput_drop_ratio)
    """

    checks: Dict[str, Dict[str, Any]] = {}
    violated = 0
    considered = 0

    def _check_spike(name: str, limit: float) -> None:
        nonlocal violated, considered
        if name not in (prev_metrics or {}) or name not in (now_metrics or {}):
            return
        pv = prev_metrics.get(name)
        nv = now_metrics.get(name)
        if not isinstance(pv, (int, float)) or not isinstance(nv, (int, float)):
            return
        r = _ratio(float(nv), float(pv))
        v = (r is not None) and (r > float(limit))
        checks[name] = {"kind": "spike", "prev": float(pv), "now": float(nv), "ratio": r, "limit": float(limit), "violated": v}
        considered += 1
        if v:
            violated += 1

    def _check_drop(name: str, floor: float) -> None:
        nonlocal violated, considered
        if name not in (prev_metrics or {}) or name not in (now_metrics or {}):
            return
        pv = prev_metrics.get(name)
        nv = now_metrics.get(name)
        if not isinstance(pv, (int, float)) or not isinstance(nv, (int, float)):
            return
        r = _ratio(float(nv), float(pv))
        v = (r is not None) and (r < float(floor))
        checks[name] = {"kind": "drop", "prev": float(pv), "now": float(nv), "ratio": r, "floor": float(floor), "violated": v}
        considered += 1
        if v:
            violated += 1

    _check_spike("latency_ms_p95", latency_spike_ratio)
    _check_spike("error_rate", error_spike_ratio)
    _check_spike("cost_units", cost_spike_ratio)
    _check_drop("throughput_per_s", throughput_drop_ratio)

    degraded_score = 0.0 if considered == 0 else float(violated) / float(considered)
    degraded_mode = degraded_score >= float(degraded_score_threshold)
    return DriftReport(degraded_mode=degraded_mode, degraded_score=degraded_score, checks=checks)

