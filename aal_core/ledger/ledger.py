from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class EvidenceLedger:
    """
    Minimal append-only JSONL ledger used for promotion scanning.

    Each line is a JSON object of shape:
      {"id": int, "utc": str, "type": str, "payload": {...}, "provenance": {...}}
    """

    ledger_path: Path
    counter_path: Path

    def _read_counter(self) -> int:
        if not self.counter_path.exists():
            return 0
        try:
            raw = json.loads(self.counter_path.read_text(encoding="utf-8") or "{}")
            return int(raw.get("next_id", 0))
        except Exception:
            return 0

    def _write_counter(self, next_id: int) -> None:
        self.counter_path.parent.mkdir(parents=True, exist_ok=True)
        self.counter_path.write_text(json.dumps({"next_id": int(next_id)}), encoding="utf-8")

    def append(self, *, entry_type: str, payload: Optional[Dict[str, Any]] = None, provenance: Optional[Dict[str, Any]] = None) -> int:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        next_id = self._read_counter()
        ent = {
            "id": int(next_id),
            "utc": datetime.now(timezone.utc).isoformat(),
            "type": str(entry_type),
            "payload": dict(payload or {}),
            "provenance": dict(provenance or {}),
        }
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ent, ensure_ascii=False) + "\n")
        self._write_counter(next_id + 1)
        return int(next_id)

    def read_tail(self, n: int) -> List[Dict[str, Any]]:
        if n <= 0 or not self.ledger_path.exists():
            return []
        # Simple tail: file sizes in tests are tiny.
        lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        out: List[Dict[str, Any]] = []
        for ln in lines[-int(n) :]:
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return out

