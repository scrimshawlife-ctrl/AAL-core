from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Set


@dataclass(frozen=True)
class IdeationConstraints:
    """
    Governance constraints for proposing novel visualization grammars.

    Canonical rule: proposals are never defaults.
    """

    max_cognitive_load: float  # 0..1
    min_information_gain: float  # 0..1
    max_redundancy: float  # 0..1
    allow_new_primitives: bool  # must be False in v1
    require_semantic_justification: bool

    @staticmethod
    def v1_default() -> "IdeationConstraints":
        return IdeationConstraints(
            max_cognitive_load=0.55,
            min_information_gain=0.15,
            max_redundancy=0.65,
            allow_new_primitives=False,
            require_semantic_justification=True,
        )

    def as_dict(self) -> Mapping[str, object]:
        return {
            "max_cognitive_load": self.max_cognitive_load,
            "min_information_gain": self.min_information_gain,
            "max_redundancy": self.max_redundancy,
            "allow_new_primitives": self.allow_new_primitives,
            "require_semantic_justification": self.require_semantic_justification,
        }


ALLOWED_PRIMITIVES: Set[str] = {
    "nodes",
    "edges",
    "fields",
    "lanes",
    "knots",
    "flows",
    "clusters",
    "grid",
    "radial",
    "timeline",
    "matrix",
    "chord",
    "arc",
    "heatmap",
}

ALLOWED_SEMANTIC_SOURCES: Set[str] = {
    "entity.kind",
    "entity.label",
    "entity.domain",
    "entity.metrics.salience",
    "entity.metrics.order",
    "edge.kind",
    "edge.resonance_magnitude",
    "edge.source_id",
    "edge.target_id",
    "time_axis.steps",
}

DEFAULT_LIMITS: Dict[str, Any] = {
    "max_primitives": 4,
    "max_layers": 4,
    "max_channels": 5,
    "max_text_density": 0.22,
}


def validate_pattern_spec(spec: Dict[str, Any], limits: Dict[str, Any] | None = None) -> None:
    lim = dict(DEFAULT_LIMITS)
    if limits:
        lim.update(limits)

    primitives = spec.get("primitives", [])
    if not isinstance(primitives, list) or not primitives:
        raise ValueError("pattern_spec.primitives must be non-empty list")
    if len(primitives) > lim["max_primitives"]:
        raise ValueError("pattern_spec exceeds max_primitives")

    for p in primitives:
        if p not in ALLOWED_PRIMITIVES:
            raise ValueError(f"illegal primitive: {p}")

    layers = spec.get("layers", [])
    if not isinstance(layers, list) or len(layers) > lim["max_layers"]:
        raise ValueError("pattern_spec exceeds max_layers")

    channels = spec.get("channels", {})
    if not isinstance(channels, dict):
        raise ValueError("pattern_spec.channels must be dict")
    if len(channels.keys()) > lim["max_channels"]:
        raise ValueError("pattern_spec exceeds max_channels")

    mappings = spec.get("mappings", [])
    if not isinstance(mappings, list):
        raise ValueError("pattern_spec.mappings must be list")

    for m in mappings:
        src = m.get("source")
        if src not in ALLOWED_SEMANTIC_SOURCES:
            raise ValueError(f"illegal semantic source: {src}")

    claims = spec.get("claims", [])
    if claims:
        raise ValueError("pattern_spec.claims not allowed (no causality assertions)")
