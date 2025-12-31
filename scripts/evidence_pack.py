#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import json

from abx_runes.yggdrasil.evidence_bundle import SCHEMA_VERSION, lock_hash, verify_hash, minimal_validate
from abx_runes.yggdrasil.hashing import canonical_json_dumps


def sha256_file(path: Path) -> str:
    """Compute SHA256 digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc() -> str:
    """Current UTC timestamp in ISO8601 format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def cmd_new(args: argparse.Namespace) -> int:
    """Create a new evidence bundle."""
    sources = []
    for u in args.url:
        sources.append({
            "kind": "url",
            "ref": u,
            "digest": hashlib.sha256(u.encode("utf-8")).hexdigest(),
            "observed_at": now_utc()
        })
    for fp in args.file:
        p = Path(fp)
        if not p.exists():
            print(f"Missing file: {p}")
            return 2
        sources.append({
            "kind": "file",
            "ref": str(p),
            "digest": sha256_file(p),
            "observed_at": now_utc()
        })
    for c in args.commit:
        sources.append({
            "kind": "commit",
            "ref": c,
            "digest": hashlib.sha256(c.encode("utf-8")).hexdigest(),
            "observed_at": now_utc()
        })
    for n in args.note:
        sources.append({
            "kind": "note",
            "ref": n,
            "digest": hashlib.sha256(n.encode("utf-8")).hexdigest(),
            "observed_at": now_utc()
        })

    claims = []
    for i, stmt in enumerate(args.claim, 1):
        claims.append({
            "id": f"claim.{i:03d}",
            "statement": stmt,
            "confidence": float(args.confidence),
            "supports": [s["ref"] for s in sources],
        })

    bridges = []
    for edge in args.bridge:
        if "->" not in edge:
            print(f"Invalid --bridge '{edge}' (expected from->to)")
            return 2
        frm, to = edge.split("->", 1)
        frm = frm.strip()
        to = to.strip()
        if not frm or not to:
            print(f"Invalid --bridge '{edge}' (empty from/to)")
            return 2
        bridges.append({"from": frm, "to": to})

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_utc(),
        "bundle_hash": "",
        "sources": sorted(sources, key=lambda x: (x["kind"], x["ref"], x["digest"])),
        "claims": claims,
        "calibration_refs": [],
        "bridges": sorted(bridges, key=lambda x: (x["from"], x["to"])),
    }
    bundle = lock_hash(bundle)

    out = Path(args.out)
    out.write_text(canonical_json_dumps(bundle) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify an evidence bundle."""
    path = Path(args.bundle)
    if not path.exists():
        print(f"Missing bundle: {path}")
        return 2
    bundle = json.loads(path.read_text(encoding="utf-8"))
    try:
        minimal_validate(bundle)
    except Exception as e:
        print(f"INVALID: {e}")
        return 3
    if not verify_hash(bundle):
        print("INVALID: bundle_hash mismatch")
        return 4
    print("OK")
    return 0


def main() -> int:
    """Main CLI entrypoint."""
    ap = argparse.ArgumentParser(description="Create/verify ABX evidence bundles.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_new = sub.add_parser("new", help="Create a new evidence bundle.")
    ap_new.add_argument("--out", required=True)
    ap_new.add_argument("--url", action="append", default=[])
    ap_new.add_argument("--file", action="append", default=[])
    ap_new.add_argument("--commit", action="append", default=[])
    ap_new.add_argument("--note", action="append", default=[])
    ap_new.add_argument("--bridge", action="append", default=[], help="Bridge edge to unlock: from->to (repeatable)")
    ap_new.add_argument("--claim", action="append", default=[], required=True)
    ap_new.add_argument("--confidence", default="0.6")
    ap_new.set_defaults(func=cmd_new)

    ap_ver = sub.add_parser("verify", help="Verify an evidence bundle hash + minimal contract.")
    ap_ver.add_argument("--bundle", required=True)
    ap_ver.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
