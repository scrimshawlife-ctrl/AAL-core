from __future__ import annotations

import argparse
import sys
from pathlib import Path

from abx_runes.yggdrasil.io import load_manifest_dict, verify_hash
from abx_runes.yggdrasil.lint import render_forbidden_crossings_report
from abx_runes.yggdrasil.evidence_loader import load_evidence_bundles
from abx_runes.yggdrasil.plan import build_execution_plan
from abx_runes.yggdrasil.schema import (
    PlanOptions,
    GovernanceSpec,
    Lane,
    NodeKind,
    PortSpec,
    PromotionState,
    ProvenanceSpec,
    Realm,
    RuneLink,
    StabilizationSpec,
    YggdrasilManifest,
    YggdrasilNode,
)
from abx_runes.yggdrasil.validate import ValidationError, validate_manifest


def _load_structured(path: Path) -> YggdrasilManifest:
    """Load manifest dict and convert to structured YggdrasilManifest."""
    d = load_manifest_dict(path)
    prov = d["provenance"]
    provenance = ProvenanceSpec(
        schema_version=str(prov["schema_version"]),
        manifest_hash=str(prov.get("manifest_hash", "")),
        created_at=str(prov.get("created_at", "")),
        updated_at=str(prov.get("updated_at", "")),
        source_commit=str(prov.get("source_commit", "")),
    )

    nodes = []
    for n in d.get("nodes", []):
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

    links = []
    for l in d.get("links", []):
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
                required_evidence_ports=tuple(PortSpec(**p) for p in l.get("required_evidence_ports", []) or []),
            )
        )

    return YggdrasilManifest(provenance=provenance, nodes=tuple(nodes), links=tuple(links))


def main() -> int:
    """
    CI-grade lint gate for YGGDRASIL-IR manifests.

    Checks:
    1. Manifest file exists
    2. Hash integrity (provenance.manifest_hash matches content)
    3. Structural validation (hard membrane rules)
    4. Forbidden crossings (shadow->forecast without explicit approval)

    Exit codes:
    0 = OK
    2 = Missing manifest file
    3 = Hash mismatch (provenance drift)
    4 = Validation error (invalid structure/governance rules)
    5 = Forbidden crossings detected
    """
    ap = argparse.ArgumentParser(description="CI-grade lint for yggdrasil.manifest.json")
    ap.add_argument("--manifest", default="yggdrasil.manifest.json", help="Path to manifest JSON")
    ap.add_argument("--evidence-bundle", action="append", default=[], help="Evidence bundle JSON path(s) to unlock bridges in optional plan check")
    args = ap.parse_args()

    path = Path(args.manifest)
    if not path.exists():
        print(f"YGGDRASIL LINT FAIL: missing {path}")
        return 2

    d = load_manifest_dict(path)
    if not verify_hash(d):
        print("YGGDRASIL LINT FAIL: provenance.manifest_hash does not match manifest content.")
        return 3

    # structural validation (includes hard membrane rules)
    try:
        m = _load_structured(path)
        validate_manifest(m)
    except ValidationError as e:
        print(f"YGGDRASIL LINT FAIL: validation error: {e}")
        return 4

    # forbidden crossings report produced by emitter in provenance.lint
    lint = d.get("provenance", {}).get("lint", {}) or {}
    forbidden = lint.get("forbidden_crossings", []) or []
    report = render_forbidden_crossings_report(forbidden)
    if forbidden:
        print(report)
        return 5

    # Optional: prove a plan can be built with provided evidence bundles (does not execute)
    if args.evidence_bundle:
        res = load_evidence_bundles(args.evidence_bundle)
        # if any are bad, fail (since user explicitly provided them)
        if res.bundle_paths_bad:
            print("YGGDRASIL LINT FAIL: provided evidence bundles invalid:")
            for b in res.bundle_paths_bad:
                print(f"- {b['path']}: {b['reason']}")
            return 6
        # build a plan with the evidence port present
        plan = build_execution_plan(m, PlanOptions(input_bundle=res.input_bundle))
        # if everything pruned, signal failure (indicates unsatisfied required ports somewhere)
        if not plan.ordered_node_ids:
            print("YGGDRASIL LINT FAIL: plan empty even with provided evidence bundles.")
            return 7

    print("YGGDRASIL LINT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
