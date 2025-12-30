from __future__ import annotations

from typing import Dict, List, Tuple

from .schema import ExecutionPlan, YggdrasilManifest, YggdrasilNode


def render_tree_view(m: YggdrasilManifest) -> str:
    """
    Governance spine: parent/child tree view (authority topology).
    """
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
    """
    Data veins: depends_on edges (DAG).
    """
    idx = m.node_index()
    lines: List[str] = []
    for nid in sorted(idx.keys()):
        n = idx[nid]
        if not n.depends_on:
            continue
        deps = ", ".join(sorted(n.depends_on))
        lines.append(f"{nid} <- [{deps}]")
    return "\n".join(lines) if lines else "(no depends_on edges)"


def render_plan(plan: ExecutionPlan) -> str:
    lines = []
    lines.append("EXECUTION PLAN (deterministic)")
    lines.append(f"kept={len(plan.ordered_node_ids)} pruned={len(plan.pruned_node_ids)}")
    lines.append("")
    lines.append("ORDER:")
    for i, nid in enumerate(plan.ordered_node_ids, 1):
        lines.append(f"{i:03d}. {nid}")
    if plan.pruned_node_ids:
        lines.append("")
        lines.append("PRUNED:")
        for nid in plan.pruned_node_ids:
            lines.append(f"- {nid}")
    return "\n".join(lines)
