from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple


class Realm(str, Enum):
    ASGARD = "ASGARD"          # promoted / governed prediction + approved metrics
    HEL = "HEL"                # shadow-only observation metrics/detectors
    MIDGARD = "MIDGARD"        # observations / world inputs
    NIFLHEIM = "NIFLHEIM"      # missingness / uncertainty / not_computable rules
    MUSPELHEIM = "MUSPELHEIM"  # generative / creative transforms


class Lane(str, Enum):
    SHADOW = "shadow"
    FORECAST = "forecast"
    NEUTRAL = "neutral"


class PromotionState(str, Enum):
    SHADOW = "shadow"
    CANDIDATE = "candidate"
    PROMOTED = "promoted"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class NodeKind(str, Enum):
    ROOT_POLICY = "root_policy"
    KERNEL = "kernel"
    REALM = "realm"
    RUNE = "rune"
    ARTIFACT = "artifact"


@dataclass(frozen=True)
class PortSpec:
    """
    Typed IO ports (minimal, stringly-typed for portability).
    """
    name: str
    dtype: str
    required: bool = True


@dataclass(frozen=True)
class StabilizationSpec:
    window_cycles: int = 0
    min_cycles_before_promotion_considered: int = 0
    decay_constant: float = 0.0


@dataclass(frozen=True)
class GovernanceSpec:
    rent_metrics: Tuple[str, ...] = ()
    gates_required: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ProvenanceSpec:
    schema_version: str
    manifest_hash: str
    created_at: str
    updated_at: str
    source_commit: str


@dataclass(frozen=True)
class YggdrasilNode:
    id: str
    kind: NodeKind
    realm: Realm
    lane: Lane
    authority_level: int

    # Tree parent (governance spine). None only for the single root node.
    parent: Optional[str] = None

    # DAG dependencies (data veins).
    depends_on: Tuple[str, ...] = ()

    inputs: Tuple[PortSpec, ...] = ()
    outputs: Tuple[PortSpec, ...] = ()

    promotion_state: PromotionState = PromotionState.SHADOW
    stabilization: StabilizationSpec = field(default_factory=StabilizationSpec)
    governance: GovernanceSpec = field(default_factory=GovernanceSpec)


@dataclass(frozen=True)
class RuneLink:
    """
    Explicit bridge for cross-realm/cross-lane wiring.
    """
    id: str
    from_node: str
    to_node: str

    # Allowed lane transitions e.g. ("forecast->forecast", "neutral->forecast")
    allowed_lanes: Tuple[str, ...] = ()

    # observation | feature | artifact_only | other
    data_class: str = "feature"

    determinism_rule: str = "stable_sort_by_id"
    failure_mode: str = "not_computable"  # not_computable | skip | fallback
    evidence_required: Tuple[str, ...] = ()
    required_evidence_ports: Tuple[PortSpec, ...] = ()


@dataclass(frozen=True)
class YggdrasilManifest:
    provenance: ProvenanceSpec
    nodes: Tuple[YggdrasilNode, ...]
    links: Tuple[RuneLink, ...] = ()

    def node_index(self) -> Dict[str, YggdrasilNode]:
        return {n.id: n for n in self.nodes}


@dataclass(frozen=True)
class PlanOptions:
    include_realms: Optional[Tuple[Realm, ...]] = None
    include_lanes: Optional[Tuple[Lane, ...]] = None
    include_kinds: Optional[Tuple[NodeKind, ...]] = None
    allow_deprecated: bool = False
    allow_archived: bool = False
    # Optional evidence/data availability for not-computable pruning
    # Type is Any (InputBundle) to avoid circular import; deterministic anyway
    input_bundle: Any = None


@dataclass(frozen=True)
class ExecutionPlan:
    ordered_node_ids: Tuple[str, ...]
    pruned_node_ids: Tuple[str, ...]
    options: PlanOptions
    planner_trace: Mapping[str, Any] = field(default_factory=dict)
