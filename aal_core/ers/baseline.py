from __future__ import annotations

from typing import Dict, Iterable, List


def _bucket(v: float, cuts: Iterable[float]) -> str:
    cuts_list: List[float] = list(cuts)
    if not cuts_list:
        raise ValueError("cuts must be non-empty")
    for c in cuts_list:
        if v <= c:
            return f"<= {c}"
    return f"> {cuts_list[-1]}"


def compute_baseline_signature(metrics: Dict) -> Dict[str, str]:
    """
    Deterministic, low-cardinality workload signature derived from existing metrics.

    v0.7 minimal fields (categorical / bucketed):
    - queue_depth_bucket: 0–10, 10–50, 50+
    - input_size_bucket: small/medium/large (<=1e3, <=1e5, >1e5)
    - mode: if present in metrics
    - time_window: coarse label (e.g., peak/offpeak) if present in metrics
    """
    sig: Dict[str, str] = {}

    q = metrics.get("queue_depth")
    if q is not None:
        sig["queue_depth_bucket"] = _bucket(float(q), [10, 50])

    s = metrics.get("input_size")
    if s is not None:
        sig["input_size_bucket"] = _bucket(float(s), [1e3, 1e5])

    mode = metrics.get("mode")
    if mode is not None:
        sig["mode"] = str(mode)

    tw = metrics.get("time_window")
    if tw is not None:
        sig["time_window"] = str(tw)

    return sig

