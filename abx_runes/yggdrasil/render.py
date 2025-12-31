from __future__ import annotations

from typing import Dict, List

from .schema import ExecutionPlan, YggdrasilManifest, YggdrasilNode


def render_tree_view(m: YggdrasilManifest) -> str:
    idx = m.node_index()
    children: Dict[str, List[str]] = {n.id: [] for n in m.nodes}
    root_id = None

    for n in m.nodes:
        if n.parent is None:
            root_id = n.id
        else:
            children[n.parent].append(n.id)

    for k in children:
        children[k].sort()

    if root_id is None:
        return "(no root)"

    lines: List[str] = []
    _render_subtree(idx, children, root_id, prefix="", is_last=True, out=lines)
    return "\n".join(lines)


def _render_subtree(
    idx: Dict[str, YggdrasilNode],
    children: Dict[str, List[str]],
    nid: str,
    prefix: str,
    is_last: bool,
    out: List[str],
) -> None:
    n = idx[nid]
    connector = "└─" if is_last else "├─"
    label = f"{nid} [{n.kind.value} | {n.realm.value} | {n.lane.value} | auth={n.authority_level} | {n.promotion_state.value}]"
    out.append(f"{prefix}{connector} {label}")

    new_prefix = prefix + ("   " if is_last else "│  ")
    kids = children.get(nid, [])
    for i, kid in enumerate(kids):
        _render_subtree(idx, children, kid, new_prefix, i == len(kids) - 1, out)


def render_veins_view(m: YggdrasilManifest) -> str:
    idx = m.node_index()
    lines: List[str] = []
    for nid in sorted(idx.keys()):
        n = idx[nid]
        if n.depends_on:
            lines.append(f"{nid} <- [{', '.join(sorted(n.depends_on))}]")
    return "\n".join(lines) if lines else "(no depends_on edges)"


def render_plan(plan: ExecutionPlan) -> str:
    lines: List[str] = []
    lines.append("EXECUTION PLAN (deterministic)")
    lines.append(f"kept={len(plan.ordered_node_ids)} pruned={len(plan.pruned_node_ids)}")
    lines.append("")
    lines.append("ORDER:")
    for i, nid in enumerate(plan.ordered_node_ids, 1):
        lines.append(f"{i:03d}. {nid}")

    # Show not-computable nodes (pruned early due to missing inputs)
    nc = dict(plan.planner_trace.get("not_computable", {}) or {})
    if nc:
        lines.append("")
        lines.append("NOT_COMPUTABLE (pruned early):")
        for nid in sorted(nc.keys()):
            lines.append(f"- {nid}: {nc[nid]}")

    if plan.pruned_node_ids:
        lines.append("")
        lines.append("PRUNED:")
        for nid in plan.pruned_node_ids:
            lines.append(f"- {nid}")
    return "\n".join(lines)
