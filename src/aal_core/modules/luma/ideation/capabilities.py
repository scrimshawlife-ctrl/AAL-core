from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class CapabilitySignature:
    id: str
    kind: str
    requires_entity_types: Set[str]
    requires_edge_types: Set[str]
    requires_attributes: Set[str]
    preferred_primitives: List[str]
    notes: str


def _sig(
    id: str,
    kind: str,
    ent: List[str],
    ed: List[str],
    attrs: List[str],
    prim: List[str],
    notes: str,
) -> CapabilitySignature:
    return CapabilitySignature(
        id=id,
        kind=kind,
        requires_entity_types=set(ent),
        requires_edge_types=set(ed),
        requires_attributes=set(attrs),
        preferred_primitives=list(prim),
        notes=notes,
    )


KNOWN_PATTERNS: Dict[str, CapabilitySignature] = {
    "domain_lattice": _sig(
        "domain_lattice",
        "pattern",
        ent=["domain", "subdomain", "motif"],
        ed=[],
        attrs=["motif.domain"],
        prim=["grid", "nodes"],
        notes="Places motifs into domain/subdomain cells when mapping exists.",
    ),
    "motif_domain_heatmap": _sig(
        "motif_domain_heatmap",
        "pattern",
        ent=["domain", "motif"],
        ed=[],
        attrs=["motif.domain", "motif.metrics.salience"],
        prim=["matrix", "heatmap"],
        notes="Incidence/heatmap of motifs vs domains.",
    ),
    "sankey_transfer": _sig(
        "sankey_transfer",
        "pattern",
        ent=["domain"],
        ed=["transfer"],
        attrs=["edge.source_id", "edge.target_id", "edge.resonance_magnitude"],
        prim=["flows"],
        notes="Flow view for sparse transfer pairs.",
    ),
    "transfer_chord": _sig(
        "transfer_chord",
        "pattern",
        ent=["domain"],
        ed=["transfer"],
        attrs=["edge.source_id", "edge.target_id", "edge.resonance_magnitude"],
        prim=["chord", "matrix"],
        notes="Chord view for dense transfer pairs.",
    ),
    "temporal_braid": _sig(
        "temporal_braid",
        "pattern",
        ent=["motif"],
        ed=[],
        attrs=["time_axis.steps"],
        prim=["timeline", "knots"],
        notes="Time-knot view for motif co-occurrence.",
    ),
}


LENS_FAMILIES: Dict[str, CapabilitySignature] = {
    "graph": _sig(
        "lens.graph",
        "lens_family",
        ent=["motif"],
        ed=["resonance", "synch", "transfer"],
        attrs=["edge.resonance_magnitude"],
        prim=["nodes", "edges"],
        notes="General graph lens for motifs+edges.",
    ),
    "matrix": _sig(
        "lens.matrix",
        "lens_family",
        ent=["domain", "motif"],
        ed=[],
        attrs=["motif.domain", "motif.metrics.salience"],
        prim=["matrix", "heatmap"],
        notes="Incidence/matrix lens (motif→domain).",
    ),
    "flow": _sig(
        "lens.flow",
        "lens_family",
        ent=["domain"],
        ed=["transfer"],
        attrs=["edge.source_id", "edge.target_id", "edge.resonance_magnitude"],
        prim=["flows"],
        notes="Flow lens for transfer edges (sankey/chord suggestion).",
    ),
    "timeline": _sig(
        "lens.timeline",
        "lens_family",
        ent=["event"],
        ed=[],
        attrs=["event.timestamp"],
        prim=["timeline"],
        notes="Timeline lens if timestamps exist.",
    ),
}


def list_known_patterns() -> List[str]:
    return sorted(KNOWN_PATTERNS.keys())


def get_signature(id: str) -> Optional[CapabilitySignature]:
    if id in KNOWN_PATTERNS:
        return KNOWN_PATTERNS[id]
    if id in LENS_FAMILIES:
        return LENS_FAMILIES[id]
    return None
