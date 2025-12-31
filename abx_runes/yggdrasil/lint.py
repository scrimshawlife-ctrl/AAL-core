from __future__ import annotations

from typing import Any, Dict, List


def render_forbidden_crossings_report(forbidden: List[Dict[str, Any]]) -> str:
    """
    Generate human-readable lint report for forbidden shadow->forecast crossings.

    These crossings require explicit RuneLink.allowed_lanes including 'shadow->forecast'
    plus evidence gating to prevent accidental contamination of forecast lane.
    """
    if not forbidden:
        return "YGGDRASIL LINT: no forbidden crossings detected."
    lines = []
    lines.append("YGGDRASIL LINT: forbidden crossings detected")
    lines.append("These require explicit RuneLink.allowed_lanes including 'shadow->forecast' plus evidence gating.")
    lines.append("")
    for item in forbidden:
        lines.append(f"- {item['from']} -> {item['to']}: {item['reason']}")
    return "\n".join(lines)
