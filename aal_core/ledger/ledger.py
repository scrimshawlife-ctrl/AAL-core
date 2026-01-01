from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from abx_runes.tuning.hashing import content_hash


GENESIS_HASH = "GENESIS"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class EvidenceLedger:
    """
    Minimal deterministic append-only ledger (v1.4 support).

    - Append-only JSONL
    - Monotonic idx
    - Hash-chain via entry_hash
    - No timestamps (caller may include in payload if desired)
    """

    ledger_path: Path = Path(".aal/evidence_ledger.jsonl")
    counter_path: Path = Path(".aal/evidence_ledger.counter.json")

    def _next_idx(self) -> int:
        c = _read_json(self.counter_path)
        n = int(c.get("next_idx", 0))
        c["next_idx"] = n + 1
        _write_json(self.counter_path, c)
        return n

    def tail_hash(self) -> str:
        if not self.ledger_path.exists():
            return GENESIS_HASH
        last: Optional[Dict[str, Any]] = None
        with self.ledger_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                last = json.loads(line)
        if not last:
            return GENESIS_HASH
        return str(last.get("entry_hash") or GENESIS_HASH)

    def append(self, *, entry_type: str, payload: Dict[str, Any], provenance: Dict[str, Any]) -> Dict[str, Any]:
        prev = self.tail_hash()
        idx = self._next_idx()
        entry = {
            "idx": idx,
            "type": str(entry_type),
            "payload": payload or {},
            "provenance": provenance or {},
            "prev_hash": prev,
            "entry_hash": "",
        }
        entry["entry_hash"] = content_hash(entry, blank_fields=("entry_hash",))
        _ensure_parent(self.ledger_path)
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def read_tail(self, n: int) -> List[Dict[str, Any]]:
        if n <= 0 or not self.ledger_path.exists():
            return []
        lines: List[str] = []
        with self.ledger_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
        tail_lines = lines[-int(n) :] if len(lines) > n else lines
        return [json.loads(x) for x in tail_lines]

