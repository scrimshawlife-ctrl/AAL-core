"""
Sport Normalizer Schema v1.0

A deterministic, sport-agnostic normalization contract that maps any sport
into NBA-grade primitives (Opportunity, Usage, Continuity, Volatility, Failure Modes).

NBA is the reference standard; other sports must explicitly diverge.

Usage:
    from normalizers import load_preset, validate_normalizer, make_provenance

    # Load NBA reference normalizer
    nba_config = load_preset("NBA")

    # Validate configuration
    validate_normalizer(nba_config)

    # Generate provenance
    provenance = make_provenance(nba_config)
"""

from .types import (
    DistributionShape,
    Primitive,
    OpportunitySpec,
    UsageSpec,
    ContinuitySpec,
    VolatilitySpec,
    FailureEffects,
    FailureModes,
    StatSpec,
    SportNormalizerConfig,
)
from .loader import load_normalizer, load_preset
from .validate import validate_normalizer
from .hash import stable_hash_dict
from .provenance import ProvenanceRecord, make_provenance, cfg_fingerprint

__version__ = "1.0.0"

__all__ = [
    # Types
    "DistributionShape",
    "Primitive",
    "OpportunitySpec",
    "UsageSpec",
    "ContinuitySpec",
    "VolatilitySpec",
    "FailureEffects",
    "FailureModes",
    "StatSpec",
    "SportNormalizerConfig",
    # Loader
    "load_normalizer",
    "load_preset",
    # Validation
    "validate_normalizer",
    # Hashing
    "stable_hash_dict",
    # Provenance
    "ProvenanceRecord",
    "make_provenance",
    "cfg_fingerprint",
]
