#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from abx_runes.yggdrasil.evidence_bundle import minimal_validate, lock_hash
from abx_runes.yggdrasil.hashing import canonical_json_dumps


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-lock (rehash) an edited ABX evidence bundle deterministically.")
    ap.add_argument("--bundle", required=True, help="Path to evidence bundle JSON")
    ap.add_argument("--out", default="", help="Optional output path (default: overwrite input)")
    args = ap.parse_args()

    p = Path(args.bundle)
    if not p.exists() or not p.is_file():
        print(f"Missing bundle: {p}")
        return 2

    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        print("INVALID: not valid JSON")
        return 3

    try:
        minimal_validate(d)
    except Exception as e:
        print(f"INVALID: contract_invalid: {e}")
        return 4

    locked = lock_hash(d)
    outp = Path(args.out) if args.out else p
    outp.write_text(canonical_json_dumps(locked) + "\n", encoding="utf-8")
    print(f"Wrote {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
