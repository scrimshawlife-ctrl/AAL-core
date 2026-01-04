"""
AAL-GIMLET Contracts
Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation

Canonical data contracts for deterministic codebase analysis and integration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum


class IdentityKind(str, Enum):
    """Classification of analyzed codebases"""
    AAL_OVERLAY = "AAL_OVERLAY"
    AAL_SUBSYSTEM = "AAL_SUBSYSTEM"
    EXTERNAL = "EXTERNAL"


class InspectMode(str, Enum):
    """Operating modes for GIMLET"""
    INSPECT = "inspect"
    INTEGRATE = "integrate"
    OPTIMIZE = "optimize"
    REPORT = "report"


@dataclass(frozen=True)
class Evidence:
    """Single piece of classification evidence"""
    file_path: str
    rule_hit: str
    confidence_contribution: float  # 0.0 to 1.0

    def __post_init__(self):
        if not 0.0 <= self.confidence_contribution <= 1.0:
            raise ValueError(f"confidence_contribution must be in [0.0, 1.0], got {self.confidence_contribution}")


@dataclass(frozen=True)
class FileInfo:
    """Deterministic file metadata"""
    path: str
    sha256: str
    size_bytes: int
    language: Optional[str]  # Detected language (py, js, md, etc.)
    is_entrypoint: bool  # Heuristic flag for main/init files


@dataclass(frozen=True)
class FileMap:
    """Normalized filesystem snapshot"""
    files: List[FileInfo]
    total_size_bytes: int
    file_count: int
    languages: List[str]  # Sorted unique list
    entrypoints: List[str]  # Sorted list of entrypoint paths


@dataclass(frozen=True)
class ProvenanceEnvelope:
    """Deterministic provenance metadata"""
    artifact_hash: str  # Hash of entire FileMap
    run_seed: Optional[str]  # SEED if provided
    tool_version: str  # GIMLET version
    timestamp_unix: int
    mode: InspectMode


@dataclass(frozen=True)
class Identity:
    """Classification result with evidence"""
    kind: IdentityKind
    confidence: float  # 0.0 to 1.0
    evidence: List[Evidence]

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.confidence > 0.0 and not self.evidence:
            raise ValueError("Non-zero confidence requires evidence")


@dataclass(frozen=True)
class IntegrationIssue:
    """Detected issue in AAL-native code"""
    severity: Literal["error", "warning", "info"]
    category: str  # "missing_test", "broken_boundary", "naming_violation", "acronym_missing"
    file_path: Optional[str]
    message: str
    suggested_fix: Optional[str] = None


@dataclass(frozen=True)
class IntegrationPatchPlan:
    """Plan for integrating AAL-native code"""
    issues: List[IntegrationIssue]
    actions: List[str]  # Human-readable action items
    auto_fixable: bool
    estimated_complexity: Literal["trivial", "moderate", "high"]


@dataclass(frozen=True)
class OptimizationPhase:
    """Single phase of external optimization roadmap"""
    phase_number: int
    name: str
    description: str
    actions: List[str]
    candidate_runes: List[str]  # Rune IDs that might be created
    estimated_effort: Literal["low", "medium", "high"]


@dataclass(frozen=True)
class OptimizationRoadmap:
    """Roadmap for converting external code to AAL"""
    phases: List[OptimizationPhase]
    total_phases: int
    summary: str

    def __post_init__(self):
        if len(self.phases) != self.total_phases:
            raise ValueError(f"phases length ({len(self.phases)}) != total_phases ({self.total_phases})")


@dataclass(frozen=True)
class ScoreComponent:
    """Single scoring dimension with evidence"""
    name: str
    score: float  # 0.0 to max_score
    max_score: float
    evidence: List[str]  # File paths or reasoning

    def __post_init__(self):
        if not 0.0 <= self.score <= self.max_score:
            raise ValueError(f"score {self.score} out of bounds [0, {self.max_score}]")


@dataclass(frozen=True)
class GimletScore:
    """GIMLET scoring result (0-100)"""
    total: float  # 0.0 to 100.0
    integratability: ScoreComponent  # max 30
    rune_fit: ScoreComponent  # max 30
    determinism_readiness: ScoreComponent  # max 20
    rent_potential: ScoreComponent  # max 20

    def __post_init__(self):
        expected = (
            self.integratability.score +
            self.rune_fit.score +
            self.determinism_readiness.score +
            self.rent_potential.score
        )
        if abs(self.total - expected) > 0.01:
            raise ValueError(f"total ({self.total}) != sum of components ({expected})")
        if not 0.0 <= self.total <= 100.0:
            raise ValueError(f"total score must be in [0, 100], got {self.total}")


@dataclass(frozen=True)
class InspectResult:
    """Complete GIMLET inspection result"""
    provenance: ProvenanceEnvelope
    file_map: FileMap
    identity: Identity
    integration_plan: Optional[IntegrationPatchPlan]  # Only for AAL_OVERLAY/AAL_SUBSYSTEM
    optimization_roadmap: Optional[OptimizationRoadmap]  # Only for EXTERNAL
    score: GimletScore

    def to_dict(self) -> Dict[str, Any]:
        """Convert to deterministic dict for serialization"""
        import json
        from dataclasses import asdict
        return asdict(self)


@dataclass(frozen=True)
class AcronymDefinition:
    """Single subsystem acronym definition"""
    canonical_name: str  # e.g., "AAL-GIMLET"
    expansion: str  # e.g., "Gateway for Integration, Modularization..."
    functional_definition: str  # One-line description
    status: Literal["active", "deprecated", "alias"]
    alias_for: Optional[str] = None  # If status == "alias"

    def __post_init__(self):
        if self.status == "alias" and not self.alias_for:
            raise ValueError("Alias status requires alias_for field")
        if self.status != "alias" and self.alias_for:
            raise ValueError("alias_for only valid for alias status")


@dataclass(frozen=True)
class AcronymRegistry:
    """Complete acronym registry"""
    definitions: List[AcronymDefinition]
    registry_hash: str  # Deterministic hash

    def get_definition(self, name: str) -> Optional[AcronymDefinition]:
        """Lookup by canonical name (case-sensitive)"""
        for d in self.definitions:
            if d.canonical_name == name:
                return d
        return None

    def validate_name(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate subsystem name against registry.
        Returns (is_valid, warning_message)
        """
        defn = self.get_definition(name)
        if defn is None:
            return (False, f"Non-canonical subsystem name: {name}")
        if defn.status == "deprecated":
            return (True, f"Warning: {name} is deprecated")
        if defn.status == "alias":
            return (True, f"Warning: {name} is an alias for {defn.alias_for}")
        return (True, None)
