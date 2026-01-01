from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bus.provenance import append_jsonl, hash_event


def _default_ledger_dir() -> Path:
    # Keep tuning-plane artifacts under .aal by default (local, repo-root scoped).
    return Path(".aal") / "ledger"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceLedger:
    """
    Append-only JSONL evidence ledger with a simple monotonic index counter.

    Each append writes one line:
      {"idx": int, "utc": str, "type": str, "payload": {...}, "provenance": {...}, "hash": str}
    """

    ledger_path: Path = _default_ledger_dir() / "evidence_ledger.jsonl"
    counter_path: Path = _default_ledger_dir() / "counter.json"

    def _read_counter(self) -> int:
        try:
            if not self.counter_path.exists():
                return 0
            raw = json.loads(self.counter_path.read_text(encoding="utf-8"))
            return int(raw.get("idx", 0) or 0)
        except Exception:
            # If counter is corrupted, fail safe by treating as empty.
            return 0

    def _write_counter(self, idx: int) -> None:
        self.counter_path.parent.mkdir(parents=True, exist_ok=True)
        self.counter_path.write_text(json.dumps({"idx": int(idx)}, sort_keys=True), encoding="utf-8")

    def append(self, *, entry_type: str, payload: Dict[str, Any], provenance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prev = self._read_counter()
        idx = prev + 1
        event: Dict[str, Any] = {
            "idx": idx,
            "utc": _utc_iso(),
            "type": str(entry_type),
            "payload": payload or {},
            "provenance": provenance or {},
        }
        event["hash"] = hash_event(event)

        append_jsonl(self.ledger_path, event)
        self._write_counter(idx)
        return event

    def tail(self, n: int) -> List[Dict[str, Any]]:
        if n <= 0:
            return []
        if not self.ledger_path.exists():
            return []
        lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        out: List[Dict[str, Any]] = []
        for ln in lines[-n:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                # Skip malformed lines (append-only; don't brick scan).
                continue
        return out

