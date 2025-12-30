from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from aal_core.yggdrasil.schema import (
    GovernanceSpec,
    Lane,
    NodeKind,
    PlanOptions,
    PortSpec,
    PromotionState,
    ProvenanceSpec,
    Realm,
    RuneLink,
    StabilizationSpec,
    YggdrasilManifest,
    YggdrasilNode,
)
from aal_core.yggdrasil.validate import validate_manifest, ValidationError
from aal_core.yggdrasil.plan import build_execution_plan
from aal_core.yggdrasil.render import render_tree_view, render_veins_view, render_plan


def _load_manifest(path: Path) -> YggdrasilManifest:
    data = json.loads(path.read_text(encoding="utf-8"))

    prov = data["provenance"]
    provenance = ProvenanceSpec(
        schema_version=str(prov["schema_version"]),
        manifest_hash=str(prov["manifest_hash"]),
        created_at=str(prov["created_at"]),
        updated_at=str(prov["updated_at"]),
        source_commit=str(prov["source_commit"]),
    )

    nodes: List[YggdrasilNode] = []
    for n in data.get("nodes", []):
        nodes.append(
            YggdrasilNode(
                id=str(n["id"]),
                kind=NodeKind(str(n["kind"])),
                realm=Realm(str(n["realm"])),
                lane=Lane(str(n["lane"])),
                authority_level=int(n["authority_level"]),
                parent=n.get("parent"),
                depends_on=tuple(n.get("depends_on", [])),
                inputs=tuple(PortSpec(**p) for p in n.get("inputs", [])),
                outputs=tuple(PortSpec(**p) for p in n.get("outputs", [])),
                promotion_state=PromotionState(str(n.get("promotion_state", "shadow"))),
                stabilization=StabilizationSpec(**n.get("stabilization", {})),
                governance=GovernanceSpec(
                    rent_metrics=tuple(n.get("governance", {}).get("rent_metrics", [])),
                    gates_required=tuple(n.get("governance", {}).get("gates_required", [])),
                ),
            )
        )

    links: List[RuneLink] = []
    for l in data.get("links", []):
        links.append(
            RuneLink(
                id=str(l["id"]),
                from_node=str(l["from_node"]),
                to_node=str(l["to_node"]),
                allowed_lanes=tuple(l.get("allowed_lanes", [])),
                data_class=str(l.get("data_class", "feature")),
                determinism_rule=str(l.get("determinism_rule", "stable_sort_by_id")),
                failure_mode=str(l.get("failure_mode", "not_computable")),
                evidence_required=tuple(l.get("evidence_required", [])),
            )
        )

    return YggdrasilManifest(provenance=provenance, nodes=tuple(nodes), links=tuple(links))


def main() -> None:
    ap = argparse.ArgumentParser(prog="aal-yggdrasil")
    ap.add_argument("manifest", type=str, help="Path to yggdrasil manifest JSON")
    ap.add_argument("--validate", action="store_true", help="Validate manifest only")
    ap.add_argument("--tree", action="store_true", help="Render governance tree view")
    ap.add_argument("--veins", action="store_true", help="Render data veins view")
    ap.add_argument("--plan", action="store_true", help="Build and print deterministic plan")
    ap.add_argument("--realm", action="append", default=None, help="Filter realm(s), repeatable")
    ap.add_argument("--lane", action="append", default=None, help="Filter lane(s), repeatable")
    args = ap.parse_args()

    m = _load_manifest(Path(args.manifest))

    try:
        validate_manifest(m)
    except ValidationError as e:
        raise SystemExit(f"VALIDATION FAILED: {e}")

    if args.validate and not (args.tree or args.veins or args.plan):
        print("VALIDATION OK")
        return

    if args.tree:
        print(render_tree_view(m))
        print("")

    if args.veins:
        print(render_veins_view(m))
        print("")

    if args.plan:
        realms = tuple(Realm(r) for r in (args.realm or [])) or None
        lanes = tuple(Lane(l) for l in (args.lane or [])) or None
        opts = PlanOptions(include_realms=realms, include_lanes=lanes)
        plan = build_execution_plan(m, opts)
        print(render_plan(plan))


if __name__ == "__main__":
    main()
