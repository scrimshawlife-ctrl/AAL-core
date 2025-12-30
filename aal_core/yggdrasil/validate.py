from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .schema import (
    Lane,
    NodeKind,
    PromotionState,
    Realm,
    RuneLink,
    YggdrasilManifest,
)


class ValidationError(Exception):
    pass


def _lane_pair(src: Lane, dst: Lane) -> str:
    return f"{src.value}->{dst.value}"


def validate_manifest(m: YggdrasilManifest) -> None:
    """
    Validates:
    - unique node IDs
    - single-root tree spine and parent references
    - authority monotonicity along parent chain
    - DAG acyclicity of depends_on (after filtering by existence)
    - lane rule: SHADOW must never flow into FORECAST via depends_on unless explicitly allowed by a RuneLink
    - realm rule: cross-realm depends_on must have a RuneLink permitting it
    """
    nodes = m.node_index()
    links = list(m.links)

    if len(nodes) != len(m.nodes):
        raise ValidationError("Duplicate node IDs detected.")

    # Tree spine checks: find roots (parent=None)
    roots = [n for n in m.nodes if n.parent is None]
    if len(roots) != 1:
        raise ValidationError(f"Expected exactly 1 root node (parent=None); found {len(roots)}.")

    # Parent existence and authority monotonicity: parent authority must be >= child authority.
    for n in m.nodes:
        if n.parent is None:
            continue
        if n.parent not in nodes:
            raise ValidationError(f"Node '{n.id}' parent '{n.parent}' does not exist.")
        p = nodes[n.parent]
        if p.authority_level < n.authority_level:
            raise ValidationError(
                f"Authority violation: parent '{p.id}' ({p.authority_level}) "
                f"< child '{n.id}' ({n.authority_level})."
            )

    # Build lookup for RuneLinks (from,to) -> link
    by_edge: Dict[Tuple[str, str], List[RuneLink]] = {}
    for l in links:
        by_edge.setdefault((l.from_node, l.to_node), []).append(l)

    def _edge_has_link(from_id: str, to_id: str) -> bool:
        return (from_id, to_id) in by_edge

    def _link_allows_lane(from_id: str, to_id: str, lane_pair: str) -> bool:
        ls = by_edge.get((from_id, to_id), [])
        return any(lane_pair in l.allowed_lanes for l in ls)

    # Lane + realm rules for depends_on edges
    for n in m.nodes:
        for dep_id in n.depends_on:
            if dep_id not in nodes:
                raise ValidationError(f"Node '{n.id}' depends_on missing node '{dep_id}'.")
            dep = nodes[dep_id]

            # Realm crossing requires a RuneLink
            if dep.realm != n.realm:
                if not _edge_has_link(dep.id, n.id):
                    raise ValidationError(
                        f"Cross-realm dependency requires RuneLink: '{dep.id}'({dep.realm}) -> '{n.id}'({n.realm})."
                    )

            # Shadow -> Forecast is illegal unless explicitly allowed by RuneLink
            if dep.lane == Lane.SHADOW and n.lane == Lane.FORECAST:
                lp = _lane_pair(dep.lane, n.lane)
                if not _link_allows_lane(dep.id, n.id, lp):
                    raise ValidationError(
                        f"Lane violation: SHADOW cannot feed FORECAST without RuneLink allowing '{lp}': "
                        f"'{dep.id}' -> '{n.id}'."
                    )

    # DAG acyclicity (depends_on graph)
    _assert_acyclic_depends_on(nodes)


def _assert_acyclic_depends_on(nodes: Dict[str, object]) -> None:
    """
    Deterministic DFS cycle check.
    """
    temp: Set[str] = set()
    perm: Set[str] = set()

    # stable traversal order
    ids = sorted(nodes.keys())

    def deps(nid: str) -> List[str]:
        n = nodes[nid]
        d = getattr(n, "depends_on", ())
        return sorted(list(d))

    def visit(nid: str) -> None:
        if nid in perm:
            return
        if nid in temp:
            raise ValidationError(f"Cycle detected in depends_on graph at '{nid}'.")
        temp.add(nid)
        for d in deps(nid):
            if d not in nodes:
                raise ValidationError(f"Missing dependency '{d}' referenced by '{nid}'.")
            visit(d)
        temp.remove(nid)
        perm.add(nid)

    for nid in ids:
        visit(nid)
