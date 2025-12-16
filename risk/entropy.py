"""
Entropy scoring for sport risk profiles.

Computes deterministic entropy scores from Sport Normalizer configurations
to quantify the stability and predictability of different sports.
"""
from typing import Dict, Tuple
from normalizers.types import SportNormalizerConfig, DistributionShape


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def _normalize_event_rate(event_rate: float) -> float:
    """Normalize event rate to [0, 1] using 100 as reference."""
    return _clamp(event_rate / 100.0, 0.0, 1.0)


def _distribution_penalty(shape: DistributionShape) -> float:
    """
    Compute entropy penalty based on distribution shape.

    More irregular distributions have higher entropy.
    """
    penalties = {
        DistributionShape.NORMAL: 0.00,
        DistributionShape.SKEWED: 0.08,
        DistributionShape.SPIKY: 0.16,
        DistributionShape.BINARY: 0.28,
    }
    return penalties[shape]


def entropy_score(cfg: SportNormalizerConfig) -> Tuple[float, Dict[str, float]]:
    """
    Compute deterministic entropy score for a sport.

    Lower entropy = more stable/predictable (NBA-like)
    Higher entropy = less stable/predictable (NFL-like)

    Args:
        cfg: SportNormalizerConfig instance

    Returns:
        Tuple of (entropy_score, breakdown_dict)
        - entropy_score: float in [0, 1]
        - breakdown: dict with component scores for transparency
    """
    # Extract normalizer values
    stability = cfg.opportunity.stability_score
    concentration = cfg.usage.concentration_score
    event_rate = cfg.continuity.event_rate
    distribution_shape = cfg.continuity.distribution_shape
    per_event_var = cfg.volatility.per_event_variance
    game_var = cfg.volatility.game_level_variance

    # Normalize event rate
    event_rate_norm = _normalize_event_rate(event_rate)

    # Base entropy (inverse of stability indicators)
    # Higher stability/concentration/event_rate → lower base entropy
    base = 1.0 - (
        0.50 * stability +
        0.20 * concentration +
        0.30 * event_rate_norm
    )

    # Distribution shape penalty
    shape_penalty = _distribution_penalty(distribution_shape)

    # Volatility penalty (clamped to max 0.60)
    vol_penalty = _clamp(
        0.35 * per_event_var + 0.35 * game_var,
        0.0,
        0.60
    )

    # Total entropy (clamped to [0, 1])
    total_entropy = _clamp(
        base + shape_penalty + vol_penalty,
        0.0,
        1.0
    )

    # Breakdown for transparency
    breakdown = {
        "base": round(base, 4),
        "shape_penalty": round(shape_penalty, 4),
        "vol_penalty": round(vol_penalty, 4),
        "total": round(total_entropy, 4),
        # Individual components
        "stability": stability,
        "concentration": concentration,
        "event_rate_norm": round(event_rate_norm, 4),
        "per_event_variance": per_event_var,
        "game_level_variance": game_var,
    }

    return total_entropy, breakdown
