from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .schema import (
    ExecutionPlan,
    Lane,
    NodeKind,
    PlanOptions,
    PromotionState,
    Realm,
    YggdrasilManifest,
    YggdrasilNode,
)
from .validate import validate_manifest


def build_execution_plan(m: YggdrasilManifest, options: PlanOptions) -> ExecutionPlan:
    """
    Deterministic planner:
    - validates manifest first
    - filters nodes by options
    - topologically sorts by depends_on
    - stable tie-breakers by node id
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

    kept_ids = {n.id for n in m.nodes if allowed(n)}
    pruned_ids = tuple(sorted({n.id for n in m.nodes} - kept_ids))

    # Build adjacency limited to kept nodes (dependencies must also be kept; otherwise prune dependent)
    # Deterministic "closure" prune: if a node depends on a pruned node, prune it too.
    changed = True
    while changed:
        changed = False
        for nid in list(kept_ids):
            n = idx[nid]
            for dep in n.depends_on:
                if dep not in kept_ids:
                    kept_ids.remove(nid)
                    changed = True
                    break

    # update pruned after closure
    pruned_ids = tuple(sorted({n.id for n in m.nodes} - kept_ids))

    order = _toposort(idx, kept_ids)

    trace = {
        "kept_count": len(kept_ids),
        "pruned_count": len(pruned_ids),
        "kept_ids": tuple(sorted(kept_ids)),
        "pruned_ids": pruned_ids,
        "toposort": "stable_by_node_id",
    }

    return ExecutionPlan(
        ordered_node_ids=tuple(order),
        pruned_node_ids=pruned_ids,
        options=options,
        planner_trace=trace,
    )


def _toposort(idx: Dict[str, YggdrasilNode], kept_ids: Set[str]) -> List[str]:
    """
    Kahn toposort with stable ordering by node id.
    """
    # in-degree counts
    indeg: Dict[str, int] = {nid: 0 for nid in kept_ids}
    deps_map: Dict[str, List[str]] = {}

    for nid in kept_ids:
        n = idx[nid]
        deps = [d for d in n.depends_on if d in kept_ids]
        deps_map[nid] = sorted(deps)
        for d in deps:
            indeg[nid] += 1

    # start nodes: indeg=0, stable order
    ready = sorted([nid for nid, deg in indeg.items() if deg == 0])

    out: List[str] = []
    while ready:
        nid = ready.pop(0)  # stable
        out.append(nid)

        # reduce indegree of nodes that depend on nid
        for kid in sorted(kept_ids):
            if nid in deps_map.get(kid, []):
                indeg[kid] -= 1
                if indeg[kid] == 0:
                    # insert in sorted order (stable)
                    if kid not in ready:
                        ready.append(kid)
                        ready.sort()

    if len(out) != len(kept_ids):
        # This should not happen if validate_manifest passed, but keep hard fail.
        missing = sorted(list(kept_ids - set(out)))
        raise RuntimeError(f"Toposort failed; nodes remaining: {missing}")

    return out
