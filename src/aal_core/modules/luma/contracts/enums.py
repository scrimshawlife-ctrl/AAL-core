from __future__ import annotations

from enum import Enum


class NotComputable(str, Enum):
    """
    Explicit missingness sentinel.

    Canonical constraint: no optional ambiguity. Missing or unavailable data is
    represented explicitly as `not_computable`, not as `None` / missing keys.
    """

    VALUE = "not_computable"


class LumaMode(str, Enum):
    STATIC = "static"
    INTERACTIVE = "interactive"
    ANIMATED = "animated"


class ArtifactKind(str, Enum):
    SVG = "svg"
    PNG = "png"
    HTML_CANVAS = "html_canvas"
    ANIMATION_PLAN_JSON = "animation_plan_json"
    NOT_COMPUTABLE = "not_computable"


class PatternKind(str, Enum):
    MOTIF_GRAPH = "motif_graph"
    DOMAIN_LATTICE = "domain_lattice"
    TEMPORAL_BRAID = "temporal_braid"
    RESONANCE_FIELD = "resonance_field"
    SANKEY_TRANSFER = "sankey_transfer"
    CLUSTER_BLOOM = "cluster_bloom"
    MOTIF_DOMAIN_HEATMAP = "motif_domain_heatmap"
    TRANSFER_CHORD = "transfer_chord"


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    REJECTED = "rejected"
    ACCEPTED_FOR_CANARY = "accepted_for_canary"
    PROMOTED = "promoted"
