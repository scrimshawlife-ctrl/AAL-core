#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from abx_runes.yggdrasil.hashing import canonical_json_dumps, sha256_hex
from abx_runes.yggdrasil.io import verify_hash


ALLOWED_PATCH_FIELDS = {"allowed_lanes", "evidence_required", "required_evidence_ports"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_link_index(manifest: Dict[str, Any], patch: Dict[str, Any]) -> int:
    links = manifest.get("links", []) or []
    pid = patch.get("id", "")
    frm = patch.get("from_node", "")
    to = patch.get("to_node", "")

    matches = []
    for i, l in enumerate(links):
        if pid and str(l.get("id", "")) == str(pid):
            matches.append(i)
            continue
        if frm and to and str(l.get("from_node", "")) == str(frm) and str(l.get("to_node", "")) == str(to):
            matches.append(i)

    if len(matches) == 0:
        raise ValueError("No matching link found for patch (by id or from_node/to_node).")
    if len(matches) > 1:
        raise ValueError("Ambiguous patch: multiple matching links found.")
    return matches[0]


def apply_patch_to_link(link: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(link)
    for k in sorted(ALLOWED_PATCH_FIELDS):
        if k in patch:
            out[k] = patch[k]
    return out


def relock_manifest_hash(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Self-hash safe: set provenance.manifest_hash="" during hashing, then fill it.
    """
    m = json.loads(canonical_json_dumps(manifest))
    prov = m.get("provenance", {})
    if not isinstance(prov, dict):
        prov = {}
    prov["manifest_hash"] = ""
    m["provenance"] = prov
    payload = canonical_json_dumps(m).encode("utf-8")
    h = sha256_hex(payload)
    m["provenance"]["manifest_hash"] = h
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply RuneLink bridge patches to yggdrasil.manifest.json safely.")
    ap.add_argument("--manifest", default="yggdrasil.manifest.json")
    ap.add_argument("--patch", action="append", required=True, help="Path to *.rune_link.patch.json (repeatable)")
    ap.add_argument("--out", default="", help="Optional output path (default: overwrite manifest)")
    ap.add_argument("--require-valid-hash", action="store_true", help="Fail if manifest hash is currently invalid")
    args = ap.parse_args()

    mp = Path(args.manifest)
    if not mp.exists():
        print(f"Missing manifest: {mp}")
        return 2
    manifest = load_json(mp)

    if args.require_valid_hash:
        if not verify_hash(manifest):
            print("FAIL: manifest_hash invalid (refuse apply with --require-valid-hash).")
            return 3

    links = manifest.get("links", []) or []
    if not isinstance(links, list):
        print("FAIL: manifest.links must be an array")
        return 4

    patches = [load_json(Path(p)) for p in args.patch]
    # deterministic apply order: sort by patch id then from/to
    def _key(p: Dict[str, Any]) -> Tuple[str, str, str]:
        return (str(p.get("id", "")), str(p.get("from_node", "")), str(p.get("to_node", "")))
    patches = sorted(patches, key=_key)

    applied = []
    for p in patches:
        unknown = set(p.keys()) - (ALLOWED_PATCH_FIELDS | {"id", "from_node", "to_node"})
        if unknown:
            print(f"FAIL: patch contains unknown fields: {sorted(unknown)}")
            return 5

        idx = find_link_index(manifest, p)
        old = links[idx]
        links[idx] = apply_patch_to_link(old, p)
        applied.append({"patch": _key(p), "link_id": str(links[idx].get("id", ""))})

    manifest["links"] = links
    manifest = relock_manifest_hash(manifest)

    outp = Path(args.out) if args.out else mp
    outp.write_text(canonical_json_dumps(manifest) + "\n", encoding="utf-8")
    print(f"Applied {len(applied)} patch(es). Wrote {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
