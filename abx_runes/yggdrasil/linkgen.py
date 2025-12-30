from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple


def stable_edge_id(from_node: str, to_node: str) -> str:
    """
    Deterministic short ID for an edge.
    """
    h = hashlib.sha256(f"{from_node}->{to_node}".encode("utf-8")).hexdigest()[:12]
    return f"link.{h}"


def lane_pair(src_lane: str, dst_lane: str) -> str:
    return f"{src_lane}->{dst_lane}"


def ensure_links_for_crossings(
    *,
    nodes_by_id: Dict[str, Dict],
    existing_links: List[Dict],
) -> Tuple[List[Dict], List[Dict]]:
    """
    Add RuneLinks deterministically for:
    - cross-realm dependencies (always)
    - any lane-pair dependencies (as metadata)

    Safe rule:
    - If src_lane == 'shadow' and dst_lane == 'forecast', DO NOT auto-allow.
      Emit a stub link with allowed_lanes=[] and record it as forbidden crossing.

    Returns: (new_links, forbidden_crossings)
    forbidden_crossings entries: {"from":..., "to":..., "reason":...}
    """
    # Index existing links by (from,to)
    have = {(l.get("from_node"), l.get("to_node")) for l in existing_links}
    out_links: List[Dict] = list(existing_links)
    forbidden: List[Dict] = []

    # Stable traversal order
    for to_id in sorted(nodes_by_id.keys()):
        to_n = nodes_by_id[to_id]
        deps = to_n.get("depends_on", []) or []
        for from_id in sorted([str(d) for d in deps]):
            if from_id not in nodes_by_id:
                continue
            from_n = nodes_by_id[from_id]

            from_realm = str(from_n.get("realm"))
            to_realm = str(to_n.get("realm"))
            from_lane = str(from_n.get("lane"))
            to_lane = str(to_n.get("lane"))

            cross_realm = (from_realm != to_realm)
            lp = lane_pair(from_lane, to_lane)

            if (from_id, to_id) in have:
                continue

            # Only create links when needed to satisfy the membrane:
            # - cross-realm always needs a link (validator requirement)
            if not cross_realm:
                continue

            # Create link
            lid = stable_edge_id(from_id, to_id)
            link = {
                "id": lid,
                "from_node": from_id,
                "to_node": to_id,
                "allowed_lanes": [],
                "data_class": "feature",
                "determinism_rule": "stable_sort_by_id",
                "failure_mode": "not_computable",
                "evidence_required": [],
            }

            # Auto-allow only if NOT shadow->forecast
            if not (from_lane == "shadow" and to_lane == "forecast"):
                link["allowed_lanes"] = [lp]
            else:
                forbidden.append({
                    "from": from_id,
                    "to": to_id,
                    "reason": "shadow->forecast requires explicit allowed_lanes + evidence bundle; auto-allow forbidden",
                })
                link["evidence_required"] = ["EXPLICIT_SHADOW_FORECAST_BRIDGE"]

            out_links.append(link)
            have.add((from_id, to_id))

    # Deterministic order for links
    out_links.sort(key=lambda x: (str(x.get("from_node")), str(x.get("to_node")), str(x.get("id"))))
    forbidden.sort(key=lambda x: (x["from"], x["to"]))
    return out_links, forbidden
