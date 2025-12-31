#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any, Dict

from abx_runes.yggdrasil.bridge_apply_core import find_link_index, validate_patch_fields
from abx_runes.yggdrasil.manifest_load import load_structured_manifest


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint bridge patch snippets against yggdrasil.manifest.json.")
    ap.add_argument("--manifest", default="yggdrasil.manifest.json")
    ap.add_argument("--patch", action="append", default=[], help="Explicit patch file (repeatable)")
    ap.add_argument("--glob", default="evidence/*.rune_link.patch.json", help="Glob for patch snippets")
    args = ap.parse_args()

    mp = Path(args.manifest)
    if not mp.exists():
        print(f"Missing manifest: {mp}")
        return 2

    # Use structured loader for parse validation, but we lint against raw dict for exact matching
    _ = load_structured_manifest(mp)
    manifest = load_json(mp)

    patch_paths = list(args.patch)
    patch_paths.extend(sorted(glob.glob(args.glob)))
    patch_paths = sorted(set(patch_paths))
    if not patch_paths:
        print("No patch snippets found.")
        return 0

    failures = 0
    for pstr in patch_paths:
        p = Path(pstr)
        if not p.exists():
            print(f"FAIL: missing patch file: {p}")
            failures += 1
            continue
        patch = load_json(p)
        ok, reason = validate_patch_fields(patch)
        if not ok:
            print(f"FAIL: {p}: {reason}")
            failures += 1
            continue
        try:
            idx = find_link_index(manifest, patch)
        except Exception as e:
            print(f"FAIL: {p}: {e}")
            failures += 1
            continue
        # Success path
        link = manifest.get("links", [])[idx]
        print(f"OK: {p} -> link_id={link.get('id')}")

    if failures:
        print(f"FAILURES: {failures}")
        return 5
    print("BRIDGE PATCH LINT OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
