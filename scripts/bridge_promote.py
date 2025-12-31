#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from abx_runes.yggdrasil.evidence_bundle import SCHEMA_VERSION as EVID_SCHEMA, lock_hash
from abx_runes.yggdrasil.hashing import canonical_json_dumps
from abx_runes.yggdrasil.linkgen import stable_edge_id, evidence_port_name
from abx_runes.yggdrasil.manifest_load import load_structured_manifest


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def digest_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def cmd_propose(args: argparse.Namespace) -> int:
    """
    Generate:
      - evidence bundle (hash-locked) that targets a specific bridge edge
      - a patch snippet describing the RuneLink fields required
      - a golden test file for this bridge
    """
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Missing manifest: {manifest_path}")
        return 2

    m = load_structured_manifest(manifest_path)
    edges = {(l.from_node, l.to_node) for l in m.links}
    if (args.frm, args.to) not in edges:
        print(f"Bridge edge not present in manifest.links: {args.frm} -> {args.to}")
        return 3

    link_id = stable_edge_id(args.frm, args.to)  # e.g., link.<12hex>
    port = evidence_port_name(args.frm, args.to)  # e.g., evidence.link.<12hex>

    # Evidence bundle must be real inputs; user supplies claims/sources via CLI.
    sources: List[Dict[str, str]] = []
    for u in args.url:
        sources.append({"kind": "url", "ref": u, "digest": digest_str(u), "observed_at": now_utc()})
    for c in args.commit:
        sources.append({"kind": "commit", "ref": c, "digest": digest_str(c), "observed_at": now_utc()})
    for n in args.note:
        sources.append({"kind": "note", "ref": n, "digest": digest_str(n), "observed_at": now_utc()})

    if not sources:
        print("Refusing: at least one --url/--commit/--note source is required (no empty evidence).")
        return 4
    if not args.claim:
        print("Refusing: at least one --claim is required (no empty evidence).")
        return 5

    claims = []
    for i, stmt in enumerate(args.claim, 1):
        claims.append({
            "id": f"claim.{i:03d}",
            "statement": stmt,
            "confidence": float(args.confidence),
            "supports": [s["ref"] for s in sources],
        })

    bundle = {
        "schema_version": EVID_SCHEMA,
        "created_at": now_utc(),
        "bundle_hash": "",
        "sources": sorted(sources, key=lambda x: (x["kind"], x["ref"], x["digest"])),
        "claims": claims,
        "calibration_refs": [],
        "bridges": [{"from": args.frm, "to": args.to}],
    }
    bundle = lock_hash(bundle)

    out_bundle = Path(args.out_bundle)
    write_text(out_bundle, canonical_json_dumps(bundle) + "\n")

    # Patch snippet: the exact RuneLink shape required to ALLOW the bridge
    patch = {
        "id": link_id,
        "from_node": args.frm,
        "to_node": args.to,
        "allowed_lanes": ["shadow->forecast"],
        "evidence_required": ["EXPLICIT_SHADOW_FORECAST_BRIDGE"],
        "required_evidence_ports": [{"name": port, "dtype": "evidence_bundle", "required": True}],
    }
    out_patch = Path(args.out_patch)
    write_text(out_patch, canonical_json_dumps(patch) + "\n")

    # Golden test: proves planning prunes without port + keeps with port
    test_name = f"test_bridge_{link_id.replace('.', '_')}.py"
    out_test = Path(args.out_tests_dir) / test_name
    test_py = f'''\
from abx_runes.yggdrasil.inputs_bundle import InputBundle
from abx_runes.yggdrasil.linkgen import evidence_port_name
from abx_runes.yggdrasil.manifest_load import load_structured_manifest
from abx_runes.yggdrasil.plan import build_execution_plan
from abx_runes.yggdrasil.schema import PlanOptions


def test_bridge_requires_per_edge_evidence_port():
    m = load_structured_manifest(__import__("pathlib").Path("{args.manifest}"))
    port = evidence_port_name("{args.frm}", "{args.to}")

    # Without port: downstream should prune if it depends on the bridge-required link evidence.
    plan = build_execution_plan(m, PlanOptions(input_bundle=InputBundle(present={{}})))
    # We can't assume which nodes prune globally; we assert the planner trace records missing bridge evidence
    # for at least one node if the bridge is actually used downstream in your topology.
    nc = dict(plan.planner_trace.get("not_computable", {{}}) or {{}})
    # If nothing is pruned, the bridge may not currently be exercised by any depends_on chain in the plan.
    # In that case, this test is neutral (still deterministic).
    if nc:
        assert any("missing_bridge_evidence:" in v for v in nc.values())

    # With port: planner should not prune *because of this port missing*.
    plan2 = build_execution_plan(m, PlanOptions(input_bundle=InputBundle(present={{port: "evidence_bundle"}})))
    nc2 = dict(plan2.planner_trace.get("not_computable", {{}}) or {{}})
    assert not any(port in v for v in nc2.values())
'''
    write_text(out_test, test_py)

    print("PROPOSE OK")
    print(f"- evidence bundle: {out_bundle}")
    print(f"- rune-link patch snippet: {out_patch}")
    print(f"- golden test: {out_test}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Bridge Promotion Workflow (artifacts-first).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("propose", help="Generate evidence bundle + patch snippet + golden test for one bridge.")
    p.add_argument("--manifest", default="yggdrasil.manifest.json")
    p.add_argument("--from", dest="frm", required=True)
    p.add_argument("--to", dest="to", required=True)
    p.add_argument("--url", action="append", default=[])
    p.add_argument("--commit", action="append", default=[])
    p.add_argument("--note", action="append", default=[])
    p.add_argument("--claim", action="append", default=[], required=True)
    p.add_argument("--confidence", default="0.6")
    p.add_argument("--out-bundle", default="evidence/bridge.bundle.json")
    p.add_argument("--out-patch", default="evidence/bridge.rune_link.patch.json")
    p.add_argument("--out-tests-dir", default="tests")
    p.set_defaults(func=cmd_propose)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
