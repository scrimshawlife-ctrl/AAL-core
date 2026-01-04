"""
AAL-GIMLET
Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation

Deterministic ingress adapter for codebase analysis and AAL-core integration.
"""

from .contracts import (
    # Core types
    IdentityKind,
    InspectMode,
    Evidence,
    FileInfo,
    FileMap,
    ProvenanceEnvelope,
    Identity,
    IntegrationIssue,
    IntegrationPatchPlan,
    OptimizationPhase,
    OptimizationRoadmap,
    ScoreComponent,
    GimletScore,
    InspectResult,
    AcronymDefinition,
    AcronymRegistry,
)

from .scan import normalize_input, cleanup_temp

from .identity import classify_identity, classify_with_manifest_validation

from .plan import build_integration_plan, build_optimization_roadmap

from .score import compute_gimlet_score

from .rune import inspect, GIMLET_RUNE_DESCRIPTOR, EXPORTS

from .registry import (
    get_canonical_registry,
    validate_subsystem_name,
    enforce_registry_on_manifest,
    get_definition,
    list_all_definitions,
)


__all__ = [
    # Contracts
    "IdentityKind",
    "InspectMode",
    "Evidence",
    "FileInfo",
    "FileMap",
    "ProvenanceEnvelope",
    "Identity",
    "IntegrationIssue",
    "IntegrationPatchPlan",
    "OptimizationPhase",
    "OptimizationRoadmap",
    "ScoreComponent",
    "GimletScore",
    "InspectResult",
    "AcronymDefinition",
    "AcronymRegistry",
    # Scan
    "normalize_input",
    "cleanup_temp",
    # Identity
    "classify_identity",
    "classify_with_manifest_validation",
    # Plan
    "build_integration_plan",
    "build_optimization_roadmap",
    # Score
    "compute_gimlet_score",
    # Rune
    "inspect",
    "GIMLET_RUNE_DESCRIPTOR",
    "EXPORTS",
    # Registry
    "get_canonical_registry",
    "validate_subsystem_name",
    "enforce_registry_on_manifest",
    "get_definition",
    "list_all_definitions",
]

__version__ = "0.1.0"
