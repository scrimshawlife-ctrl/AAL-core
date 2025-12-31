"""ϟ₄ SDS: State-Dependent Susceptibility gating operator.

Computes a gate state (CLOSED, LIMINAL, OPEN) based on user state vector
and contextual factors. Controls access depth and modality.

No network calls. Deterministic given inputs.
"""

from __future__ import annotations
from typing import Any, Dict


def apply_sds(
    state_vector: Dict[str, float],
    context: Dict[str, Any],
    interaction_kind: str = "oracle"
) -> Dict[str, Any]:
    """
    Compute gate state and susceptibility score.

    Args:
        state_vector: User state dimensions (0.0-1.0 scalars)
            Expected keys: arousal, valence, cognitive_load, openness
            Missing keys default to 0.5 (neutral)
        context: Environmental/temporal context
            Optional keys: time_of_day, session_count, last_interaction_delta_hours
        interaction_kind: Type of interaction ("oracle", "query", etc.)

    Returns:
        {
            "gate_state": "CLOSED" | "LIMINAL" | "OPEN",
            "susceptibility_score": float (0.0-1.0),
            "factors": {
                "arousal_factor": float,
                "openness_factor": float,
                "context_factor": float
            },
            "rune_id": "ϟ₄"
        }
    """
    # Extract state vector with defaults
    arousal = state_vector.get("arousal", 0.5)
    valence = state_vector.get("valence", 0.5)
    cognitive_load = state_vector.get("cognitive_load", 0.5)
    openness = state_vector.get("openness", 0.5)

    # Normalize to [0, 1]
    arousal = max(0.0, min(1.0, arousal))
    valence = max(0.0, min(1.0, valence))
    cognitive_load = max(0.0, min(1.0, cognitive_load))
    openness = max(0.0, min(1.0, openness))

    # Context factors
    time_of_day = context.get("time_of_day", "unknown")
    session_count = context.get("session_count", 1)
    last_delta = context.get("last_interaction_delta_hours", 24.0)

    # Compute factor weights
    # High arousal + low cognitive load = more open
    arousal_factor = arousal * (1.0 - cognitive_load * 0.5)

    # Openness trait directly contributes
    openness_factor = openness

    # Context: evening hours + longer gaps = more receptive
    context_factor = 0.5
    if time_of_day in ("evening", "night"):
        context_factor += 0.2
    if last_delta > 12.0:
        context_factor += 0.15
    if session_count < 3:
        context_factor += 0.15
    context_factor = min(1.0, context_factor)

    # Aggregate susceptibility score
    susceptibility_score = (
        arousal_factor * 0.35 +
        openness_factor * 0.40 +
        context_factor * 0.25
    )

    # Gate state thresholds
    if susceptibility_score < 0.35:
        gate_state = "CLOSED"
    elif susceptibility_score < 0.65:
        gate_state = "LIMINAL"
    else:
        gate_state = "OPEN"

    return {
        "gate_state": gate_state,
        "susceptibility_score": round(susceptibility_score, 3),
        "factors": {
            "arousal_factor": round(arousal_factor, 3),
            "openness_factor": round(openness_factor, 3),
            "context_factor": round(context_factor, 3)
        },
        "rune_id": "ϟ₄"
    }
