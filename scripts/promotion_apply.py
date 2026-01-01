#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from aal_core.governance.promotion_executor import apply_approved_promotions


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply explicitly approved promotions (v2.0).")
    ap.add_argument("--proposals", type=str, required=True, help="Path to Proposal IR JSON list")
    ap.add_argument(
        "--approve",
        action="append",
        default=[],
        help="Approved proposal_hash to execute (repeatable)",
    )
    args = ap.parse_args()

    proposals = json.loads(Path(args.proposals).read_text(encoding="utf-8"))
    approved = [p for p in (proposals or []) if p.get("proposal_hash") in set(args.approve)]
    if not approved:
        print("no approved proposals selected")
        return 0

    # Runtime wiring is deployment-specific (registry, effects_store, metrics providers).
    # v2.0 ships the executor + policy store + evidence receipts. The CLI enforces explicit
    # approvals and leaves runtime injection to the host integration.
    raise SystemExit(
        "promotion_apply is intentionally not auto-wired.\n"
        "Integrate by calling apply_approved_promotions(...)\n"
        "with a registry + effects_store + metric/assignment providers from your runtime."
    )


if __name__ == "__main__":
    raise SystemExit(main())

