"""
Provenance tracking for risk policy enforcement.
"""
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any
from normalizers.types import SportNormalizerConfig
from normalizers.hash import stable_hash_dict
from .policy import LegSpec


@dataclass(frozen=True)
class RiskProvenanceRecord:
    """Audit trail for risk policy enforcement."""
    created_at_iso: str
    sport_id: str
    mode: str
    normalizer_hash: str
    entropy_score: float
    throttle_hash: str
    inputs_hash: str


def _hash_throttle_limits(limits: Dict[str, Any]) -> str:
    """Hash throttle limits for provenance."""
    # Extract hashable fields only
    hashable = {
        "max_legs": limits["max_legs"],
        "min_survivability": limits["min_survivability"],
        "allow_event_primitives": limits["allow_event_primitives"],
        "max_same_team_legs": limits["max_same_team_legs"],
        "max_high_variance_legs": limits["max_high_variance_legs"],
    }
    return stable_hash_dict(hashable)


def _hash_legs(legs: List[LegSpec]) -> str:
    """Hash leg specifications for provenance."""
    legs_data = [
        {
            "sport_id": leg.sport_id,
            "stat_id": leg.stat_id,
            "team_id": leg.team_id,
            "primitive": leg.primitive,
            "survivability_score": leg.survivability_score,
        }
        for leg in legs
    ]
    return stable_hash_dict({"legs": legs_data})


def make_risk_provenance(
    cfg: SportNormalizerConfig,
    mode: str,
    entropy_score: float,
    throttle_limits: Dict[str, Any],
    legs: List[LegSpec]
) -> RiskProvenanceRecord:
    """
    Create provenance record for risk policy enforcement.

    Args:
        cfg: SportNormalizerConfig instance
        mode: Policy mode
        entropy_score: Computed entropy score
        throttle_limits: Throttle recommendations
        legs: Leg specifications

    Returns:
        RiskProvenanceRecord with full audit trail
    """
    # Hash normalizer config
    normalizer_hash = stable_hash_dict(cfg.to_dict())

    # Hash throttle limits
    throttle_hash = _hash_throttle_limits(throttle_limits)

    # Hash input legs
    inputs_hash = _hash_legs(legs)

    return RiskProvenanceRecord(
        created_at_iso=datetime.utcnow().isoformat(),
        sport_id=cfg.sport_id,
        mode=mode,
        normalizer_hash=normalizer_hash,
        entropy_score=round(entropy_score, 4),
        throttle_hash=throttle_hash,
        inputs_hash=inputs_hash,
    )
