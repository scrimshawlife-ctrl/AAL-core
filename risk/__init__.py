"""
Cross-Sport Entropy Throttle (CSET) for risk management.

Provides deterministic parlay risk assessment based on sport normalizers:
- Entropy scoring from normalizer configurations
- Mode-based throttle recommendations
- Policy enforcement with leg filtering
- Full provenance tracking

Usage:
    from normalizers import load_preset
    from risk import entropy_score, recommend_limits, enforce_policy, LegSpec

    # Load sport normalizer
    nba = load_preset("NBA")

    # Compute entropy
    entropy, breakdown = entropy_score(nba)

    # Get recommendations
    limits = recommend_limits(nba, "ultra_safe")

    # Enforce policy
    legs = [LegSpec("NBA", "points", "LAL", "usage", 0.55), ...]
    result = enforce_policy(nba, "ultra_safe", legs)
"""

from .entropy import entropy_score
from .throttle import recommend_limits, ULTRA_SAFE, BALANCED, CORRELATED, LADDER, MODES
from .policy import LegSpec, enforce_policy
from .provenance import RiskProvenanceRecord, make_risk_provenance

__version__ = "1.0.0"

__all__ = [
    # Entropy
    "entropy_score",
    # Throttle
    "recommend_limits",
    "ULTRA_SAFE",
    "BALANCED",
    "CORRELATED",
    "LADDER",
    "MODES",
    # Policy
    "LegSpec",
    "enforce_policy",
    # Provenance
    "RiskProvenanceRecord",
    "make_risk_provenance",
]
