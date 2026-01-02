from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

LEDGER_SCHEMA = "LumaProposalLedger.v0"


@dataclass(frozen=True)
class LedgerEntry:
    ts_utc: str
    action: str
    proposal_id: str
    proposal_sha256: str
    scene_hash: str
    actor: str
    payload: Dict[str, Any]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_json(obj: Any) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(data)


def load_ledger(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"schema": LEDGER_SCHEMA, "entries": []}
    raw = p.read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    if obj.get("schema") != LEDGER_SCHEMA:
        raise ValueError(f"ledger schema mismatch: {obj.get('schema')}")
    if "entries" not in obj or not isinstance(obj["entries"], list):
        raise ValueError("ledger missing entries[]")
    return obj


def append_entry(path: str, entry: LedgerEntry) -> Dict[str, Any]:
    obj = load_ledger(path)
    entries = obj["entries"]

    entries.append(entry.__dict__)

    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)

    return {"path": path, "count": len(entries), "ledger_sha256": _sha256_bytes(data)}


def proposal_payload_sha256(proposal_obj: Dict[str, Any]) -> str:
    return _sha256_json(proposal_obj)


def ledger_status(ledger_obj: Dict[str, Any]) -> Dict[str, str]:
    status: Dict[str, str] = {}
    for e in ledger_obj.get("entries", []):
        pid = e.get("proposal_id")
        action = e.get("action")
        if not pid or not action:
            continue
        if action == "accepted_for_canary":
            status[pid] = "accepted_for_canary"
        elif action == "rejected":
            status[pid] = "rejected"
        elif action == "proposed_exported" and pid not in status:
            status[pid] = "proposed"
    return status


def make_entry(
    action: str,
    proposal_id: str,
    proposal_sha256: str,
    scene_hash: str,
    actor: str,
    payload: Dict[str, Any],
) -> LedgerEntry:
    return LedgerEntry(
        ts_utc=_now_utc(),
        action=action,
        proposal_id=proposal_id,
        proposal_sha256=proposal_sha256,
        scene_hash=scene_hash,
        actor=actor,
        payload=payload or {},
    )
