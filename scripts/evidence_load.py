#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from abx_runes.yggdrasil.evidence_loader import load_evidence_bundles, load_evidence_bundles_for_manifest
from abx_runes.yggdrasil.hashing import canonical_json_dumps
from scripts.yggdrasil_lint import _load_structured


def main() -> int:
    """Load + verify evidence bundle files and output planning ports."""
    ap = argparse.ArgumentParser(description="Load + verify evidence bundle files and output planning ports.")
    ap.add_argument("--bundle", action="append", default=[], help="Path to an evidence bundle JSON (repeatable)")
    ap.add_argument("--manifest", default="", help="Optional yggdrasil.manifest.json; if provided, bridges must exist in manifest.links")
    ap.add_argument("--out", default="", help="Optional output JSON file for ports (else print)")
    args = ap.parse_args()

    if args.manifest:
        m = _load_structured(Path(args.manifest))
        res = load_evidence_bundles_for_manifest(args.bundle, m)
    else:
        res = load_evidence_bundles(args.bundle)

    out = {
        "bundle_paths_ok": list(res.bundle_paths_ok),
        "bundle_paths_bad": list(res.bundle_paths_bad),
        "ports_present": dict(res.input_bundle.present),
    }

    payload = canonical_json_dumps(out) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
        print(f"Wrote {args.out}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
