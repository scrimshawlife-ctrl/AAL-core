from __future__ import annotations

from typing import Dict, List, Set

from .schema import ExecutionPlan, PlanOptions, PromotionState, YggdrasilManifest, YggdrasilNode
from .validate import validate_manifest


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
