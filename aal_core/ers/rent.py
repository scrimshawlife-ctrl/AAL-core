from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RentThresholds:
    """
    Rent-payment thresholds.
    Use >= for improvements that should go up (throughput),
    use <= for improvements that should go down (latency, cost, error).
    """
    max_latency_ms_p95: Optional[float] = None
    max_cost_units: Optional[float] = None
    max_error_rate: Optional[float] = None
    min_throughput_per_s: Optional[float] = None


def _get(m: Dict, k: str) -> Optional[float]:
    v = m.get(k)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def rent_paid(before: Dict, after: Dict, th: RentThresholds) -> Tuple[bool, str]:
    """
    Deterministic rent check using absolute thresholds on AFTER metrics.
    (v0.2 keeps it simple; v0.3 can add delta-based + significance tests.)
    """
    lat = _get(after, "latency_ms_p95")
    cost = _get(after, "cost_units")
    err = _get(after, "error_rate")
    thr = _get(after, "throughput_per_s")

    if th.max_latency_ms_p95 is not None and lat is not None and lat > th.max_latency_ms_p95:
        return False, "latency_fail"
    if th.max_cost_units is not None and cost is not None and cost > th.max_cost_units:
        return False, "cost_fail"
    if th.max_error_rate is not None and err is not None and err > th.max_error_rate:
        return False, "error_fail"
    if th.min_throughput_per_s is not None and thr is not None and thr < th.min_throughput_per_s:
        return False, "throughput_fail"
    return True, "ok"
