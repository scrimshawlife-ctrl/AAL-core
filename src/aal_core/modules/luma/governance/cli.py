from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ledger import ledger_status, load_ledger
from .ops import accept_for_canary, add_note, record_exported_proposals, reject


def _load_proposals(path: str):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, list):
        raise ValueError("proposals json must be list")
    return obj


def _find(proposals, proposal_id: str):
    for p in proposals:
        if p.get("proposal_id") == proposal_id:
            return p
    raise ValueError(f"proposal_id not found in proposals file: {proposal_id}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="luma-proposals")
    ap.add_argument("--ledger", default=".aal/luma_proposals_ledger.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("record-export", help="record exported proposals into ledger")
    s1.add_argument("--proposals", required=True)
    s1.add_argument("--actor", default="ci")

    sub.add_parser("status", help="show latest status per proposal_id")

    s3 = sub.add_parser("accept", help="accept a proposal for canary")
    s3.add_argument("--proposals", required=True)
    s3.add_argument("--id", required=True)
    s3.add_argument("--actor", required=True)
    s3.add_argument("--note", default="")

    s4 = sub.add_parser("reject", help="reject a proposal")
    s4.add_argument("--proposals", required=True)
    s4.add_argument("--id", required=True)
    s4.add_argument("--actor", required=True)
    s4.add_argument("--reason", required=True)

    s5 = sub.add_parser("note", help="add a note to a proposal_id")
    s5.add_argument("--id", required=True)
    s5.add_argument("--actor", required=True)
    s5.add_argument("--note", required=True)

    args = ap.parse_args()

    if args.cmd == "record-export":
        out = record_exported_proposals(args.ledger, args.proposals, actor=args.actor)
        print(json.dumps(out, indent=2))
        return

    if args.cmd == "status":
        led = load_ledger(args.ledger)
        st = ledger_status(led)
        print(json.dumps(st, indent=2, sort_keys=True))
        return

    if args.cmd == "accept":
        proposals = _load_proposals(args.proposals)
        p = _find(proposals, args.id)
        out = accept_for_canary(args.ledger, p, actor=args.actor, note=args.note)
        print(json.dumps(out, indent=2))
        return

    if args.cmd == "reject":
        proposals = _load_proposals(args.proposals)
        p = _find(proposals, args.id)
        out = reject(args.ledger, p, actor=args.actor, reason=args.reason)
        print(json.dumps(out, indent=2))
        return

    if args.cmd == "note":
        out = add_note(args.ledger, args.id, actor=args.actor, note=args.note)
        print(json.dumps(out, indent=2))
        return


if __name__ == "__main__":
    main()
