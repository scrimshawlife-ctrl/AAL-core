from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from abx_runes.tuning.hashing import canonical_json_dumps, sha256_hex


DEFAULT_LEDGER_PATH = Path(".aal/ledger.jsonl")


@dataclass
class EvidenceLedger:
    """
    Minimal append-only evidence ledger (JSONL).

    Entry shape:
      - idx: int (monotonic)
      - type: str
      - payload: dict
      - provenance: dict
    """

    path: Path = DEFAULT_LEDGER_PATH

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def read_tail(self, n: int) -> List[Dict[str, Any]]:
        """
        Return the last n parsed entries (oldest->newest).
        """
        if n <= 0:
            return []
        all_entries = self._read_all()
        return all_entries[-n:]

    def tail_hash(self) -> str:
        """
        Hash of the latest entry (or empty string if none).
        """
        tail = self.read_tail(1)
        if not tail:
            return ""
        return sha256_hex(canonical_json_dumps(tail[0]).encode("utf-8"))

    def append(
        self,
        *,
        entry_type: str,
        payload: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tail = self.read_tail(1)
        next_idx = int(tail[-1]["idx"]) + 1 if tail else 1
        entry = {
            "idx": next_idx,
            "type": str(entry_type),
            "payload": payload or {},
            "provenance": provenance or {},
        }

        with self.path.open("a", encoding="utf-8") as f:
            f.write(canonical_json_dumps(entry) + "\n")
        return entry

