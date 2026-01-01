from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DriftReport:
    schema_version: str
    drift_score: float  # 0..1
    degraded_mode: bool
    reasons: List[str]
    features: Dict[str, float]


def _f(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _ratio(now: Optional[float], prev: Optional[float]) -> Optional[float]:
    if now is None or prev is None:
        return None
    if prev == 0:
        return None
    return now / prev


def compute_drift(
    *,
    prev_metrics: Dict[str, Any],
    now_metrics: Dict[str, Any],
    # thresholds
    latency_spike_ratio: float = 1.25,
    error_spike_ratio: float = 1.50,
    cost_spike_ratio: float = 1.25,
    throughput_drop_ratio: float = 0.80,
    # scoring weights (kept simple & deterministic)
    w_latency: float = 0.35,
    w_error: float = 0.35,
    w_cost: float = 0.20,
    w_throughput: float = 0.10,
    degraded_score_threshold: float = 0.60,
) -> DriftReport:
    """
    Deterministic drift sentinel.

    Drift score is a weighted sum of “badness” signals (each 0..1), derived from
    ratios vs previous cycle (or last stable).
    """
    reasons: List[str] = []

    prev_lat = _f(prev_metrics.get("latency_ms_p95"))
    now_lat = _f(now_metrics.get("latency_ms_p95"))
    prev_err = _f(prev_metrics.get("error_rate"))
    now_err = _f(now_metrics.get("error_rate"))
    prev_cost = _f(prev_metrics.get("cost_units"))
    now_cost = _f(now_metrics.get("cost_units"))
    prev_thr = _f(prev_metrics.get("throughput_per_s"))
    now_thr = _f(now_metrics.get("throughput_per_s"))

    r_lat = _ratio(now_lat, prev_lat)
    r_err = _ratio(now_err, prev_err)
    r_cost = _ratio(now_cost, prev_cost)
    r_thr = _ratio(now_thr, prev_thr)

    def clamp01(x: float) -> float:
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    # Convert ratios into “badness” in 0..1 (piecewise linear ramps).
    b_lat = 0.0
    if r_lat is not None and r_lat >= latency_spike_ratio:
        b_lat = clamp01((r_lat - latency_spike_ratio) / max(1e-9, (2.0 - latency_spike_ratio)))
        reasons.append("latency_spike")

    b_err = 0.0
    if r_err is not None and r_err >= error_spike_ratio:
        b_err = clamp01((r_err - error_spike_ratio) / max(1e-9, (3.0 - error_spike_ratio)))
        reasons.append("error_spike")

    b_cost = 0.0
    if r_cost is not None and r_cost >= cost_spike_ratio:
        b_cost = clamp01((r_cost - cost_spike_ratio) / max(1e-9, (2.0 - cost_spike_ratio)))
        reasons.append("cost_spike")

    b_thr = 0.0
    if r_thr is not None and r_thr <= throughput_drop_ratio:
        # worse when ratio is smaller
        b_thr = clamp01((throughput_drop_ratio - r_thr) / max(1e-9, throughput_drop_ratio))
        reasons.append("throughput_drop")

    drift = clamp01((w_latency * b_lat) + (w_error * b_err) + (w_cost * b_cost) + (w_throughput * b_thr))
    degraded = drift >= float(degraded_score_threshold)

    return DriftReport(
        schema_version="drift-report/0.1",
        drift_score=float(drift),
        degraded_mode=bool(degraded),
        reasons=reasons,
        features={
            "ratio_latency": float(r_lat) if r_lat is not None else -1.0,
            "ratio_error": float(r_err) if r_err is not None else -1.0,
            "ratio_cost": float(r_cost) if r_cost is not None else -1.0,
            "ratio_throughput": float(r_thr) if r_thr is not None else -1.0,
            "b_lat": float(b_lat),
            "b_err": float(b_err),
            "b_cost": float(b_cost),
            "b_thr": float(b_thr),
        },
    )

