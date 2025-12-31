#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from abx_runes.yggdrasil.evidence_bundle import minimal_validate, verify_hash
from abx_runes.yggdrasil.manifest_load import load_structured_manifest


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_bridge_enabled(link: Dict[str, Any]) -> bool:
    lanes = set(link.get("allowed_lanes", []) or [])
    tags = set(link.get("evidence_required", []) or [])
    ports = link.get("required_evidence_ports", []) or []
    has_port = any(
        isinstance(p, dict)
        and bool(p.get("required", False))
        and str(p.get("dtype", "")) == "evidence_bundle"
        and str(p.get("name", "")).strip()
        for p in ports
    )
    return ("shadow->forecast" in lanes) and ("EXPLICIT_SHADOW_FORECAST_BRIDGE" in tags) and has_port


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint that enabled shadow->forecast bridges are unlockable by evidence bundles.")
    ap.add_argument("--manifest", default="yggdrasil.manifest.json")
    ap.add_argument("--evidence-glob", default="evidence/*.bundle.json")
    ap.add_argument("--fail-on-invalid-bundles", action="store_true", help="If set, invalid bundle files cause failure.")
    args = ap.parse_args()

    mp = Path(args.manifest)
    if not mp.exists():
        print(f"Missing manifest: {mp}")
        return 2

    # parse manifest structurally (typed) but lint against raw dict
    _ = load_structured_manifest(mp)
    manifest = load_json(mp)

    links = manifest.get("links", []) or []
    enabled_edges: List[Tuple[str, str, str]] = []  # (from,to,link_id)
    for l in links:
        if is_bridge_enabled(l):
            enabled_edges.append((str(l.get("from_node", "")), str(l.get("to_node", "")), str(l.get("id", ""))))

    if not enabled_edges:
        print("No enabled shadow->forecast bridges found. OK.")
        return 0

    bundle_paths = sorted(glob.glob(args.evidence_glob))
    if not bundle_paths:
        print("FAIL: enabled bridges exist but no evidence bundles found.")
        for frm, to, lid in enabled_edges:
            print(f"- enabled bridge: {lid} {frm}->{to}")
        return 5

    # Build set of unlockable edges from verified bundles
    unlockable: Set[Tuple[str, str]] = set()
    invalid: List[Tuple[str, str]] = []

    for pstr in bundle_paths:
        p = Path(pstr)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            invalid.append((pstr, "invalid_json"))
            continue
        try:
            minimal_validate(d)
        except Exception:
            invalid.append((pstr, "contract_invalid"))
            continue
        if not verify_hash(d):
            invalid.append((pstr, "hash_mismatch"))
            continue
        for b in (d.get("bridges", []) or []):
            frm = str(b.get("from", "")).strip()
            to = str(b.get("to", "")).strip()
            if frm and to:
                unlockable.add((frm, to))

    if invalid:
        print("WARN: invalid evidence bundles found:")
        for pstr, reason in sorted(invalid, key=lambda x: (x[1], x[0])):
            print(f"- {pstr}: {reason}")
        if args.fail_on_invalid_bundles:
            return 6

    failures = 0
    for frm, to, lid in enabled_edges:
        if (frm, to) not in unlockable:
            print(f"FAIL: enabled bridge not unlockable by any verified bundle: {lid} {frm}->{to}")
            failures += 1

    if failures:
        return 7

    print("BRIDGE UNLOCKABILITY LINT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
