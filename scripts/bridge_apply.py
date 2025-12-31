#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from abx_runes.yggdrasil.hashing import canonical_json_dumps
from abx_runes.yggdrasil.io import verify_hash
from abx_runes.yggdrasil.bridge_apply_core import (
    apply_patch_to_link,
    find_link_index,
    relock_manifest_hash,
    validate_patch_fields,
)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
        ok, reason = validate_patch_fields(p)
        if not ok:
            print(f"FAIL: patch invalid: {reason}")
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
