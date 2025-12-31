from __future__ import annotations

from typing import Dict, List, Set

from .schema import ExecutionPlan, PlanOptions, PromotionState, YggdrasilManifest, YggdrasilNode, RuneLink
from .validate import validate_manifest
from .inputs_bundle import InputBundle


def build_execution_plan(m: YggdrasilManifest, options: PlanOptions) -> ExecutionPlan:
    """
    Deterministic planner:
    - validates manifest
    - filters nodes by options
    - closure-prunes nodes whose dependencies were pruned
    - stable toposort by node id
    """
    validate_manifest(m)
    idx = m.node_index()
    bundle = options.input_bundle if isinstance(options.input_bundle, InputBundle) else None

    def allowed(n: YggdrasilNode) -> bool:
        if options.include_realms is not None and n.realm not in options.include_realms:
            return False
        if options.include_lanes is not None and n.lane not in options.include_lanes:
            return False
        if options.include_kinds is not None and n.kind not in options.include_kinds:
            return False
        if not options.allow_deprecated and n.promotion_state == PromotionState.DEPRECATED:
            return False
        if not options.allow_archived and n.promotion_state == PromotionState.ARCHIVED:
            return False
        return True

    kept: Set[str] = {n.id for n in m.nodes if allowed(n)}

    # index links by edge
    links_by_edge: Dict[tuple, List[RuneLink]] = {}
    for l in m.links:
        links_by_edge.setdefault((l.from_node, l.to_node), []).append(l)

    def _required_bridge_ports(from_id: str, to_id: str):
        ls = links_by_edge.get((from_id, to_id), [])
        # deterministic: merge required ports across links (should usually be 1 link)
        ports = []
        for l in sorted(ls, key=lambda x: x.id):
            ports.extend(list(getattr(l, "required_evidence_ports", ()) or ()))
        return tuple(ports)

    # not-computable pruning: required inputs missing from bundle
    not_computable_reasons: Dict[str, str] = {}
    if bundle is not None:
        for nid in sorted(list(kept)):
            n = idx[nid]
            missing = bundle.missing_required(n.inputs)
            if missing:
                kept.remove(nid)
                not_computable_reasons[nid] = f"missing_required_inputs:{','.join(missing)}"

        # bridge evidence pruning: cross-realm deps may require evidence ports on the link
        for nid in sorted(list(kept)):
            n = idx[nid]
            missing_ports = []
            for dep_id in sorted(list(n.depends_on)):
                if dep_id not in idx:
                    continue
                dep = idx[dep_id]
                if dep.realm != n.realm:
                    req_ports = _required_bridge_ports(dep_id, nid)
                    # Require all required ports be present in the bundle
                    for p in req_ports:
                        if p.required and not bundle.has(p.name, p.dtype):
                            missing_ports.append(p.name)
            if missing_ports:
                kept.remove(nid)
                not_computable_reasons[nid] = f"missing_bridge_evidence:{','.join(sorted(set(missing_ports)))}"

    # closure prune: if you depend on something pruned, you get pruned too
    changed = True
    while changed:
        changed = False
        for nid in list(kept):
            n = idx[nid]
            if any(dep not in kept for dep in n.depends_on):
                kept.remove(nid)
                changed = True

    pruned = tuple(sorted(set(idx.keys()) - kept))
    order = _toposort(idx, kept)

    trace = {
        "kept_count": len(kept),
        "pruned_count": len(pruned),
        "toposort": "stable_by_node_id",
        "not_computable": {k: not_computable_reasons[k] for k in sorted(not_computable_reasons.keys())},
    }
    return ExecutionPlan(
        ordered_node_ids=tuple(order),
        pruned_node_ids=pruned,
        options=options,
        planner_trace=trace,
    )


def _toposort(idx: Dict[str, YggdrasilNode], kept: Set[str]) -> List[str]:
    indeg: Dict[str, int] = {nid: 0 for nid in kept}
    deps: Dict[str, List[str]] = {}

    for nid in kept:
        d = [x for x in idx[nid].depends_on if x in kept]
        deps[nid] = sorted(d)
        indeg[nid] = len(d)

    ready = sorted([nid for nid, deg in indeg.items() if deg == 0])
    out: List[str] = []

    while ready:
        nid = ready.pop(0)  # stable
        out.append(nid)
        for kid in sorted(kept):
            if nid in deps.get(kid, []):
                indeg[kid] -= 1
                if indeg[kid] == 0:
                    ready.append(kid)
                    ready.sort()

    if len(out) != len(kept):
        missing = sorted(list(kept - set(out)))
        raise RuntimeError(f"Toposort failed; nodes remaining: {missing}")

    return out
