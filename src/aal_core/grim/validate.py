"""Validation for GRIM catalog graph integrity."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .model import GrimCatalog, RuneEdge


def validate_catalog(catalog: GrimCatalog) -> Dict[str, Any]:
    rune_ids = set(catalog.runes.keys())
    edges = _collect_edges(catalog)
    dangling = [edge for edge in edges if edge.dst_id not in rune_ids]

    inbound = {rune_id: 0 for rune_id in rune_ids}
    for edge in edges:
        if edge.dst_id in inbound:
            inbound[edge.dst_id] += 1
    orphans = [rid for rid, count in inbound.items() if count == 0 and not catalog.runes[rid].edges_out]

    report = {
        "summary": {
            "rune_count": len(rune_ids),
            "edge_count": len(edges),
            "dangling_edge_count": len(dangling),
            "orphan_rune_count": len(orphans),
            "has_dangling_edges": bool(dangling),
        },
        "dangling_edges": [edge.to_dict() for edge in sorted(dangling, key=_edge_key)],
        "orphan_runes": sorted(orphans),
    }
    return report


def _collect_edges(catalog: GrimCatalog) -> List[RuneEdge]:
    edges: List[RuneEdge] = []
    for rune_id in sorted(catalog.runes):
        edges.extend(catalog.runes[rune_id].edges_out)
    return sorted(edges, key=_edge_key)


def _edge_key(edge: RuneEdge) -> Tuple[str, str, str]:
    return (edge.src_id, edge.dst_id, edge.kind)
