#!/usr/bin/env python3
from __future__ import annotations

import argparse

from aal_core.ers.safe_set_store import SafeSetStore
from aal_core.governance.safe_set_builder import build_safe_sets
from aal_core.ledger.ledger import EvidenceLedger


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=20000)
    ap.add_argument("--min-attempts", type=int, default=10)
    ap.add_argument("--max-rr", type=float, default=0.05)
    ap.add_argument("--decay", type=int, default=2000)
    args = ap.parse_args()

    ledger = EvidenceLedger()
    store = SafeSetStore.load()
    res = build_safe_sets(
        ledger=ledger,
        store=store,
        tail_n=args.tail,
        policy={
            "min_attempts": args.min_attempts,
            "safe_max_rollback_rate": args.max_rr,
            "safe_set_decay_cycles": args.decay,
        },
    )
    store.save()
    print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

