"""
Type definitions for sport normalizer schema.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class DistributionShape(Enum):
    """Statistical distribution of events."""
    NORMAL = "normal"
    SKEWED = "skewed"
    SPIKY = "spiky"
    BINARY = "binary"


class Primitive(Enum):
    """Stat primitive categories."""
    OPPORTUNITY = "opportunity"
    USAGE = "usage"
    HYBRID = "hybrid"
    EVENT = "event"


@dataclass(frozen=True)
class OpportunitySpec:
    """Opportunity primitive specification."""
    unit: str
    stability_score: float

    def __post_init__(self):
        if not 0.0 <= self.stability_score <= 1.0:
            raise ValueError(f"stability_score must be in [0,1], got {self.stability_score}")


@dataclass(frozen=True)
class UsageSpec:
    """Usage primitive specification."""
    unit: str
    concentration_score: float

    def __post_init__(self):
        if not 0.0 <= self.concentration_score <= 1.0:
            raise ValueError(f"concentration_score must be in [0,1], got {self.concentration_score}")


@dataclass(frozen=True)
class ContinuitySpec:
    """Event flow and distribution characteristics."""
    event_rate: float
    distribution_shape: DistributionShape

    def __post_init__(self):
        if self.event_rate < 0.0:
            raise ValueError(f"event_rate must be >= 0, got {self.event_rate}")


@dataclass(frozen=True)
class VolatilitySpec:
    """Variance characteristics at different scales."""
    per_event_variance: float
    game_level_variance: float

    def __post_init__(self):
        if self.per_event_variance < 0.0:
            raise ValueError(f"per_event_variance must be >= 0, got {self.per_event_variance}")
        if self.game_level_variance < 0.0:
            raise ValueError(f"game_level_variance must be >= 0, got {self.game_level_variance}")


@dataclass(frozen=True)
class FailureEffects:
    """Effects of bad script on stats."""
    suppresses: List[str]
    inflates: List[str]


@dataclass(frozen=True)
class FailureModes:
    """Bad script detection and effects."""
    bad_script_definition: str
    bad_script_effects: FailureEffects


@dataclass(frozen=True)
class StatSpec:
    """Per-stat primitive mapping."""
    primitive: Primitive
    survivability_score: float

    def __post_init__(self):
        if not 0.0 <= self.survivability_score <= 1.0:
            raise ValueError(f"survivability_score must be in [0,1], got {self.survivability_score}")


@dataclass(frozen=True)
class SportNormalizerConfig:
    """Complete sport normalizer configuration."""
    schema_version: str
    sport_id: str
    version: str
    opportunity: OpportunitySpec
    usage: UsageSpec
    continuity: ContinuitySpec
    volatility: VolatilitySpec
    failure_modes: FailureModes
    stat_map: Dict[str, StatSpec]
    meta: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.schema_version != "1.0":
            raise ValueError(f"schema_version must be '1.0', got '{self.schema_version}'")
        if not self.stat_map:
            raise ValueError("stat_map cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for hashing and serialization."""
        return {
            "schema_version": self.schema_version,
            "sport_id": self.sport_id,
            "version": self.version,
            "opportunity": {
                "unit": self.opportunity.unit,
                "stability_score": self.opportunity.stability_score,
            },
            "usage": {
                "unit": self.usage.unit,
                "concentration_score": self.usage.concentration_score,
            },
            "continuity": {
                "event_rate": self.continuity.event_rate,
                "distribution_shape": self.continuity.distribution_shape.value,
            },
            "volatility": {
                "per_event_variance": self.volatility.per_event_variance,
                "game_level_variance": self.volatility.game_level_variance,
            },
            "failure_modes": {
                "bad_script_definition": self.failure_modes.bad_script_definition,
                "bad_script_effects": {
                    "suppresses": list(self.failure_modes.bad_script_effects.suppresses),
                    "inflates": list(self.failure_modes.bad_script_effects.inflates),
                },
            },
            "stat_map": {
                stat_id: {
                    "primitive": spec.primitive.value,
                    "survivability_score": spec.survivability_score,
                }
                for stat_id, spec in self.stat_map.items()
            },
            "meta": self.meta,
        }
