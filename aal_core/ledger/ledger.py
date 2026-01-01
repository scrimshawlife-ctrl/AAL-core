from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from abx_runes.tuning.hashing import canonical_json_dumps


DEFAULT_LEDGER_PATH = Path(".aal/evidence_ledger.jsonl")


@dataclass(frozen=True)
class EvidenceLedger:
    """
    Minimal append-only JSONL evidence ledger with a monotonic integer `idx`.

    This is ledger-index based (not wall clock) so governance can be deterministic.
    """

    path: Path = DEFAULT_LEDGER_PATH

    def _read_all_lines(self) -> List[str]:
        if not self.path.exists():
            return []
        txt = self.path.read_text(encoding="utf-8").strip()
        if not txt:
            return []
        return txt.split("\n")

    def _last_idx(self) -> int:
        lines = self._read_all_lines()
        if not lines:
            return -1
        try:
            last = json.loads(lines[-1])
            return int(last.get("idx", -1))
        except Exception:
            # If corrupted, treat as empty rather than crashing.
            return -1

    def append(
        self,
        *,
        entry_type: str,
        payload: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        idx = self._last_idx() + 1
        entry: Dict[str, Any] = {
            "idx": int(idx),
            "type": str(entry_type),
            "payload": payload or {},
            "provenance": provenance or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(canonical_json_dumps(entry) + "\n")
        return entry

    def read_tail(self, n: int) -> List[Dict[str, Any]]:
        lines = self._read_all_lines()
        if not lines:
            return []
        tail = lines[-int(n) :] if int(n) > 0 else []
        out: List[Dict[str, Any]] = []
        for line in tail:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

