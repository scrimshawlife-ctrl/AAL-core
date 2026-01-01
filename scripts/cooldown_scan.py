#!/usr/bin/env python3
from __future__ import annotations

import argparse

from aal_core.ers.cooldown import CooldownStore
from aal_core.governance.cooldown_scanner import run_cooldown_scan
from aal_core.ledger.ledger import EvidenceLedger


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=5000)
    ap.add_argument("--cooldown-cycles", type=int, default=250)
    ap.add_argument("--max-rollback-rate", type=float, default=0.25)
    args = ap.parse_args()

    ledger = EvidenceLedger()
    store = CooldownStore.load()
    res = run_cooldown_scan(
        ledger=ledger,
        store=store,
        tail_n=args.tail,
        policy={"cooldown_cycles": args.cooldown_cycles, "max_rollback_rate": args.max_rollback_rate},
    )
    store.save()
    print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

