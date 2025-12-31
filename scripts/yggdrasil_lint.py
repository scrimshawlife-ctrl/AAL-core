from __future__ import annotations

import argparse
import sys
from pathlib import Path

from abx_runes.yggdrasil.io import load_manifest_dict, verify_hash
from abx_runes.yggdrasil.lint import render_forbidden_crossings_report
from abx_runes.yggdrasil.evidence_loader import load_evidence_bundles
from abx_runes.yggdrasil.manifest_load import load_structured_manifest
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
        m = load_structured_manifest(path)
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
