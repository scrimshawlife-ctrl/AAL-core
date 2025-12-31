from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .schema import Lane, RuneLink, YggdrasilManifest, YggdrasilNode


class ValidationError(Exception):
    pass


def _lane_pair(src: Lane, dst: Lane) -> str:
    return f"{src.value}->{dst.value}"


def validate_manifest(m: YggdrasilManifest) -> None:
    nodes = m.node_index()
    if len(nodes) != len(m.nodes):
        raise ValidationError("Duplicate node IDs detected.")

    roots = [n for n in m.nodes if n.parent is None]
    if len(roots) != 1:
        raise ValidationError(f"Expected exactly 1 root node (parent=None); found {len(roots)}.")

    # Parent existence + authority monotonicity
    for n in m.nodes:
        if n.parent is None:
            continue
        if n.parent not in nodes:
            raise ValidationError(f"Node '{n.id}' parent '{n.parent}' does not exist.")
        p = nodes[n.parent]
        if p.authority_level < n.authority_level:
            raise ValidationError(
                f"Authority violation: parent '{p.id}' ({p.authority_level}) < child '{n.id}' ({n.authority_level})."
            )

    # Edge->links index
    by_edge: Dict[Tuple[str, str], List[RuneLink]] = {}
    for l in m.links:
        by_edge.setdefault((l.from_node, l.to_node), []).append(l)

    def has_link(frm: str, to: str) -> bool:
        return (frm, to) in by_edge

    def link_allows_lane(frm: str, to: str, lp: str) -> bool:
        return any(lp in l.allowed_lanes for l in by_edge.get((frm, to), []))

    def link_requires_evidence_tag(frm: str, to: str, tag: str) -> bool:
        return any(tag in (l.evidence_required or ()) for l in by_edge.get((frm, to), []))

    def link_requires_port(frm: str, to: str, port_name: str, dtype: str) -> bool:
        for l in by_edge.get((frm, to), []):
            ports = getattr(l, "required_evidence_ports", ()) or ()
            for p in ports:
                if p.name == port_name and p.dtype == dtype and bool(p.required):
                    return True
        return False

    # Lane + realm + existence rules over depends_on
    for n in m.nodes:
        for dep_id in n.depends_on:
            if dep_id not in nodes:
                raise ValidationError(f"Node '{n.id}' depends_on missing node '{dep_id}'.")
            dep = nodes[dep_id]

            lp = _lane_pair(dep.lane, n.lane)

            # Cross-realm requires explicit link
            if dep.realm != n.realm:
                if not has_link(dep.id, n.id):
                    raise ValidationError(
                        f"Cross-realm dependency requires RuneLink: '{dep.id}'({dep.realm.value}) -> '{n.id}'({n.realm.value})."
                    )
                # Hard membrane: link must explicitly allow the actual lane-pair
                if not link_allows_lane(dep.id, n.id, lp):
                    raise ValidationError(
                        f"Cross-realm RuneLink must allow lane-pair '{lp}': '{dep.id}' -> '{n.id}'."
                    )

            # SHADOW -> FORECAST forbidden unless link explicitly allows it
            if dep.lane == Lane.SHADOW and n.lane == Lane.FORECAST:
                if not link_allows_lane(dep.id, n.id, lp):
                    raise ValidationError(
                        f"Lane violation: SHADOW cannot feed FORECAST without RuneLink allowing '{lp}': '{dep.id}' -> '{n.id}'."
                    )
                # And must carry explicit evidence tag
                if not link_requires_evidence_tag(dep.id, n.id, "EXPLICIT_SHADOW_FORECAST_BRIDGE"):
                    raise ValidationError(
                        f"shadow->forecast bridge requires evidence_required tag 'EXPLICIT_SHADOW_FORECAST_BRIDGE': '{dep.id}' -> '{n.id}'."
                    )
                # And must require explicit evidence port (structural contract)
                if not link_requires_port(dep.id, n.id, "explicit_shadow_forecast_bridge", "evidence_bundle"):
                    raise ValidationError(
                        f"shadow->forecast bridge requires required_evidence_ports including explicit_shadow_forecast_bridge:evidence_bundle: '{dep.id}' -> '{n.id}'."
                    )

    _assert_acyclic_depends_on(nodes)


def _assert_acyclic_depends_on(nodes: Dict[str, YggdrasilNode]) -> None:
    temp: Set[str] = set()
    perm: Set[str] = set()

    def deps(nid: str) -> List[str]:
        return sorted(list(nodes[nid].depends_on))

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

    for nid in sorted(nodes.keys()):
        visit(nid)
