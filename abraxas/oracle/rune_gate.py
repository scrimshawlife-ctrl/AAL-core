"""Oracle gating and IPL window scheduling.

Integrates SDS (ϟ₄) gating and IPL (ϟ₅) insight scheduling for oracle execution.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from abraxas.runes.operators.sds import apply_sds
from abraxas.runes.operators.ipl import apply_ipl


def compute_gate(
    state_vector: Dict[str, float],
    context: Dict[str, Any],
    interaction_kind: str = "oracle"
) -> Dict[str, Any]:
    """
    Compute gate state using SDS (ϟ₄).

    Args:
        state_vector: User state dimensions (arousal, valence, cognitive_load, openness)
        context: Environmental/temporal context
        interaction_kind: Type of interaction (default: "oracle")

    Returns:
        SDS gate bundle with gate_state, susceptibility_score, factors
    """
    return apply_sds(state_vector, context, interaction_kind)


def enforce_depth(gate_bundle: Dict[str, Any], requested_depth: str) -> str:
    """
    Map gate state to effective depth level.

    Args:
        gate_bundle: Output from compute_gate() containing gate_state
        requested_depth: User's requested depth ("grounding", "shallow", "deep")

    Returns:
        Effective depth level to apply

    Mapping:
        - CLOSED -> "grounding" (regardless of request)
        - LIMINAL -> "shallow" (cap at shallow)
        - OPEN -> requested_depth (allow full depth)
    """
    gate_state = gate_bundle.get("gate_state", "CLOSED")

    if gate_state == "CLOSED":
        return "grounding"
    elif gate_state == "LIMINAL":
        # Cap at shallow, but allow grounding if requested
        if requested_depth == "grounding":
            return "grounding"
        return "shallow"
    else:  # OPEN
        return requested_depth


def schedule_insight_window(
    phase_series: Optional[List[Tuple[float, float]]],
    gate_bundle: Dict[str, Any],
    window_s: float = 2.0,
    lock_threshold: float = 0.35,
    refractory_s: float = 8.0
) -> Dict[str, Any]:
    """
    Schedule insight delivery windows using IPL (ϟ₅).

    Args:
        phase_series: Optional list of (timestamp_s, phase_value) tuples
            If None or gate not OPEN, returns empty schedule
        gate_bundle: Output from compute_gate() containing gate_state
        window_s: Duration of each insight window (default: 2.0s)
        lock_threshold: Phase threshold to trigger window (default: 0.35)
        refractory_s: Minimum gap between windows (default: 8.0s)

    Returns:
        IPL schedule bundle with events list and coverage metrics
    """
    gate_state = gate_bundle.get("gate_state", "CLOSED")

    return apply_ipl(
        phase_series=phase_series,
        gate_state=gate_state,
        window_s=window_s,
        lock_threshold=lock_threshold,
        refractory_s=refractory_s
    )
