#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

def main() -> int:
    # Allow running as a plain script without installing the package.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from aal_core.governance.promotion_scanner import scan_for_promotions
    from aal_core.ledger.ledger import EvidenceLedger

    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=2000)
    ap.add_argument("--out", type=str, required=True)
    ap.add_argument("--append-ledger", action="store_true")
    ap.add_argument("--cycle-id", type=str, default="manual")
    ap.add_argument("--effects-path", type=str, default=".aal/effects_store.json")
    args = ap.parse_args()

    ledger = EvidenceLedger()
    proposals = scan_for_promotions(
        source_cycle_id=args.cycle_id,
        ledger=ledger,
        tail_n=args.tail,
        effects_path=args.effects_path,
    )

    Path(args.out).write_text(json.dumps(proposals, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.append_ledger:
        for p in proposals:
            ledger.append(
                entry_type="promotion_proposed",
                payload={"proposal": p},
                provenance=p.get("provenance") or {},
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

