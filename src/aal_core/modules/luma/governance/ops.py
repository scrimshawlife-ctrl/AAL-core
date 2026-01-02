from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .ledger import (
    append_entry,
    ledger_status,
    load_ledger,
    make_entry,
    proposal_payload_sha256,
)


def record_exported_proposals(
    ledger_path: str, proposals_json_path: str, actor: str = "ci"
) -> Dict[str, Any]:
    p = Path(proposals_json_path)
    proposals = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(proposals, list):
        raise ValueError("proposals json must be list")

    ledger_obj = load_ledger(ledger_path)
    st = ledger_status(ledger_obj)

    out = {"recorded": 0, "skipped_existing": 0}
    for item in proposals:
        pid = item.get("proposal_id")
        if not pid:
            continue
        if st.get(pid) in ("proposed", "accepted_for_canary", "rejected"):
            out["skipped_existing"] += 1
            continue
        sha = proposal_payload_sha256(item)
        scene_hash = (item.get("provenance") or {}).get("scene_hash", "")
        append_entry(
            ledger_path,
            make_entry(
                action="proposed_exported",
                proposal_id=pid,
                proposal_sha256=sha,
                scene_hash=scene_hash,
                actor=actor,
                payload={"source_file": str(p.name)},
            ),
        )
        out["recorded"] += 1

    return out


def accept_for_canary(
    ledger_path: str, proposal_obj: Dict[str, Any], actor: str, note: str = ""
) -> Dict[str, Any]:
    pid = proposal_obj.get("proposal_id")
    if not pid:
        raise ValueError("proposal missing proposal_id")
    sha = proposal_payload_sha256(proposal_obj)
    scene_hash = (proposal_obj.get("provenance") or {}).get("scene_hash", "")

    ledger_obj = load_ledger(ledger_path)
    st = ledger_status(ledger_obj).get(pid)
    if st == "rejected":
        raise ValueError("cannot accept rejected proposal (append a note instead)")

    return append_entry(
        ledger_path,
        make_entry(
            action="accepted_for_canary",
            proposal_id=pid,
            proposal_sha256=sha,
            scene_hash=scene_hash,
            actor=actor,
            payload={"note": note},
        ),
    )


def reject(
    ledger_path: str, proposal_obj: Dict[str, Any], actor: str, reason: str
) -> Dict[str, Any]:
    pid = proposal_obj.get("proposal_id")
    if not pid:
        raise ValueError("proposal missing proposal_id")
    sha = proposal_payload_sha256(proposal_obj)
    scene_hash = (proposal_obj.get("provenance") or {}).get("scene_hash", "")

    return append_entry(
        ledger_path,
        make_entry(
            action="rejected",
            proposal_id=pid,
            proposal_sha256=sha,
            scene_hash=scene_hash,
            actor=actor,
            payload={"reason": reason},
        ),
    )


def add_note(ledger_path: str, proposal_id: str, actor: str, note: str) -> Dict[str, Any]:
    ledger_obj = load_ledger(ledger_path)
    scene_hash = ""
    proposal_sha = ""
    for e in reversed(ledger_obj.get("entries", [])):
        if e.get("proposal_id") == proposal_id:
            scene_hash = e.get("scene_hash", "")
            proposal_sha = e.get("proposal_sha256", "")
            break

    if not proposal_sha:
        proposal_sha = "unknown"

    return append_entry(
        ledger_path,
        make_entry(
            action="note",
            proposal_id=proposal_id,
            proposal_sha256=proposal_sha,
            scene_hash=scene_hash,
            actor=actor,
            payload={"note": note},
        ),
    )
