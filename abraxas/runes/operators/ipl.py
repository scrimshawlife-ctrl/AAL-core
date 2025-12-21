"""ϟ₅ IPL: Insight Phase Lock scheduling operator.

Schedules optimal insight delivery windows based on phase series
and refractory/lock logic. Controls timing of high-impact content.

No network calls. Deterministic given inputs.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


def apply_ipl(
    phase_series: Optional[List[Tuple[float, float]]] = None,
    gate_state: str = "OPEN",
    window_s: float = 2.0,
    lock_threshold: float = 0.35,
    refractory_s: float = 8.0
) -> Dict[str, Any]:
    """
    Schedule insight delivery windows with phase-lock logic.

    Args:
        phase_series: List of (timestamp_offset_s, phase_value) tuples
            phase_value in [0.0, 1.0] where peaks indicate optimal windows
            If None, returns empty schedule (gate not OPEN or no data)
        gate_state: Current gate state from SDS
        window_s: Duration of each insight window in seconds
        lock_threshold: Phase value threshold to trigger window
        refractory_s: Minimum gap between windows

    Returns:
        {
            "events": List[{
                "start_s": float,
                "duration_s": float,
                "phase_peak": float,
                "window_type": "primary" | "secondary"
            }],
            "total_windows": int,
            "coverage_ratio": float (0.0-1.0),
            "rune_id": "ϟ₅"
        }
    """
    if gate_state != "OPEN" or phase_series is None or not phase_series:
        return {
            "events": [],
            "total_windows": 0,
            "coverage_ratio": 0.0,
            "rune_id": "ϟ₅"
        }

    # Sort phase series by timestamp
    sorted_series = sorted(phase_series, key=lambda x: x[0])

    events = []
    last_event_end = -refractory_s  # Allow first event immediately

    for i, (ts, phase) in enumerate(sorted_series):
        # Check if this is a local peak above threshold
        is_peak = phase >= lock_threshold

        # Check local maxima (simple: higher than neighbors)
        if i > 0 and sorted_series[i-1][1] >= phase:
            is_peak = False
        if i < len(sorted_series) - 1 and sorted_series[i+1][1] >= phase:
            is_peak = False

        # Check refractory period
        if is_peak and ts >= last_event_end + refractory_s:
            window_type = "primary" if phase >= 0.65 else "secondary"
            events.append({
                "start_s": round(ts, 2),
                "duration_s": window_s,
                "phase_peak": round(phase, 3),
                "window_type": window_type
            })
            last_event_end = ts + window_s

    # Compute coverage ratio
    total_duration = sorted_series[-1][0] - sorted_series[0][0] if sorted_series else 0.0
    coverage = sum(e["duration_s"] for e in events) / max(1.0, total_duration)

    return {
        "events": events,
        "total_windows": len(events),
        "coverage_ratio": round(min(1.0, coverage), 3),
        "rune_id": "ϟ₅"
    }
