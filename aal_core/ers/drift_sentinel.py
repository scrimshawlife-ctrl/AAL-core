from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def _ratio(now: Optional[float], prev: Optional[float]) -> Optional[float]:
    if now is None or prev is None:
        return None
    p = float(prev)
    if p == 0.0:
        return None
    return float(now) / p


@dataclass(frozen=True)
class DriftReport:
    """
    Deterministic drift classifier for canary rollback.

    Notes:
    - We treat increases in latency/error/cost as bad, and drops in throughput as bad.
    - The `degraded_score` is a simple (deterministic) fraction of triggered checks.
    """

    latency_ratio: Optional[float]
    error_ratio: Optional[float]
    cost_ratio: Optional[float]
    throughput_ratio: Optional[float]

    latency_spike: bool
    error_spike: bool
    cost_spike: bool
    throughput_drop: bool

    degraded_score: float
    degraded_mode: bool

    # extra context for debugging / evidence
    prev_metrics: Dict[str, Any]
    now_metrics: Dict[str, Any]


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
    Compute deterministic drift report from two metrics snapshots.
    """
    prev = prev_metrics or {}
    now = now_metrics or {}

    prev_lat = prev.get("latency_ms_p95")
    now_lat = now.get("latency_ms_p95")
    prev_err = prev.get("error_rate")
    now_err = now.get("error_rate")
    prev_cost = prev.get("cost_units")
    now_cost = now.get("cost_units")
    prev_tp = prev.get("throughput_per_s")
    now_tp = now.get("throughput_per_s")

    lat_r = _ratio(now_lat, prev_lat)
    err_r = _ratio(now_err, prev_err)
    cost_r = _ratio(now_cost, prev_cost)
    tp_r = _ratio(now_tp, prev_tp)

    latency_spike = bool(lat_r is not None and lat_r >= float(latency_spike_ratio))
    error_spike = bool(err_r is not None and err_r >= float(error_spike_ratio))
    cost_spike = bool(cost_r is not None and cost_r >= float(cost_spike_ratio))
    throughput_drop = bool(tp_r is not None and tp_r <= float(throughput_drop_ratio))

    checks = [latency_spike, error_spike, cost_spike, throughput_drop]
    degraded_score = float(sum(1 for c in checks if c)) / float(len(checks))
    degraded_mode = bool(degraded_score >= float(degraded_score_threshold))

    return DriftReport(
        latency_ratio=lat_r,
        error_ratio=err_r,
        cost_ratio=cost_r,
        throughput_ratio=tp_r,
        latency_spike=latency_spike,
        error_spike=error_spike,
        cost_spike=cost_spike,
        throughput_drop=throughput_drop,
        degraded_score=degraded_score,
        degraded_mode=degraded_mode,
        prev_metrics=dict(prev),
        now_metrics=dict(now),
    )

