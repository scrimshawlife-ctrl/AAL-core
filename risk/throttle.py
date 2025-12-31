"""
Throttle recommendations based on entropy scores.

Provides mode-based leg count and quality recommendations for parlays.
"""
from typing import Dict, Any
from normalizers.types import SportNormalizerConfig
from .entropy import entropy_score


# Mode definitions
ULTRA_SAFE = "ultra_safe"
BALANCED = "balanced"
CORRELATED = "correlated"
LADDER = "ladder"

MODES = [ULTRA_SAFE, BALANCED, CORRELATED, LADDER]


def _get_max_legs(entropy: float, mode: str) -> int:
    """
    Determine max parlay legs based on entropy and mode.

    Lower entropy sports allow more legs.
    """
    if entropy <= 0.35:  # NBA-ish
        return {
            ULTRA_SAFE: 5,
            BALANCED: 6,
            CORRELATED: 5,
            LADDER: 4,
        }[mode]
    elif entropy <= 0.55:  # NHL-ish
        return {
            ULTRA_SAFE: 4,
            BALANCED: 5,
            CORRELATED: 4,
            LADDER: 3,
        }[mode]
    elif entropy <= 0.75:  # NFL-ish
        return {
            ULTRA_SAFE: 3,
            BALANCED: 4,
            CORRELATED: 4,
            LADDER: 3,
        }[mode]
    else:  # Very high entropy
        return {
            ULTRA_SAFE: 2,
            BALANCED: 3,
            CORRELATED: 3,
            LADDER: 2,
        }[mode]


def _get_min_survivability(mode: str) -> float:
    """Get minimum survivability threshold for mode."""
    return {
        ULTRA_SAFE: 0.70,
        BALANCED: 0.60,
        CORRELATED: 0.55,
        LADDER: 0.55,
    }[mode]


def _allow_event_primitives(entropy: float, mode: str) -> bool:
    """
    Determine if event primitives (rare events) are allowed.

    Ultra-safe never allows event primitives.
    Others allow only for low-entropy sports.
    """
    if mode == ULTRA_SAFE:
        return False
    return entropy < 0.80


def _get_max_same_team_legs(entropy: float, mode: str) -> int:
    """
    Determine max legs from same team.

    Lower entropy allows more same-team correlation.
    """
    if mode == ULTRA_SAFE:
        return 1 if entropy > 0.35 else 2
    elif mode == BALANCED:
        return 2 if entropy <= 0.55 else 1
    else:  # CORRELATED, LADDER
        return 3 if entropy <= 0.35 else 2


def _get_max_high_variance_legs(mode: str) -> int:
    """
    Determine max legs with survivability below threshold.

    High variance = stats with survivability < min_survivability
    """
    return {
        ULTRA_SAFE: 0,
        BALANCED: 1,
        CORRELATED: 1,
        LADDER: 0,
    }[mode]


def recommend_limits(cfg: SportNormalizerConfig, mode: str) -> Dict[str, Any]:
    """
    Generate parlay limits based on sport entropy and mode.

    Args:
        cfg: SportNormalizerConfig instance
        mode: One of ultra_safe, balanced, correlated, ladder

    Returns:
        Dictionary with:
        - max_legs: int
        - min_survivability: float
        - allow_event_primitives: bool
        - max_same_team_legs: int
        - max_high_variance_legs: int
        - entropy_score: float
        - notes: str

    Raises:
        ValueError: If mode is invalid
    """
    if mode not in MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {MODES}")

    # Compute entropy
    entropy, breakdown = entropy_score(cfg)

    # Determine limits
    max_legs = _get_max_legs(entropy, mode)
    min_survivability = _get_min_survivability(mode)
    allow_events = _allow_event_primitives(entropy, mode)
    max_same_team = _get_max_same_team_legs(entropy, mode)
    max_high_var = _get_max_high_variance_legs(mode)

    # Generate notes
    if entropy <= 0.35:
        risk_level = "low"
    elif entropy <= 0.55:
        risk_level = "moderate"
    elif entropy <= 0.75:
        risk_level = "high"
    else:
        risk_level = "very high"

    notes = (
        f"{cfg.sport_id} has {risk_level} entropy ({entropy:.3f}). "
        f"Mode '{mode}' recommends max {max_legs} legs with "
        f"min survivability {min_survivability:.2f}."
    )

    return {
        "max_legs": max_legs,
        "min_survivability": min_survivability,
        "allow_event_primitives": allow_events,
        "max_same_team_legs": max_same_team,
        "max_high_variance_legs": max_high_var,
        "entropy_score": round(entropy, 4),
        "entropy_breakdown": breakdown,
        "notes": notes,
    }
