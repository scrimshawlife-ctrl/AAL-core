from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from abx_runes.tuning.hashing import canonical_json_dumps


DEFAULT_LEDGER_PATH = Path(".aal/evidence_ledger.jsonl")


@dataclass(frozen=True)
class LedgerAppendResult:
    idx: int
    entry: Dict[str, Any]


class EvidenceLedger:
    """
    Minimal append-only JSONL evidence ledger.

    - Deterministic serialization (sorted keys, compact separators)
    - Monotonic integer idx (derived from file tail)
    """

    def __init__(self, path: Optional[Path] = None, ledger_path: Optional[Path] = None, counter_path: Optional[Path] = None):
        # Support both old and new parameter names
        if ledger_path is not None:
            self.path = ledger_path
        elif path is not None:
            self.path = path
        else:
            self.path = DEFAULT_LEDGER_PATH

        # counter_path is accepted but not used (for backward compatibility)
        self.counter_path = counter_path

        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_last_idx(self) -> int:
        if not self.path.exists():
            return -1
        try:
            with self.path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                if size <= 0:
                    return -1
                # Read last ~64KB to find final line.
                f.seek(max(0, size - 65536), 0)
                tail = f.read().decode("utf-8", errors="replace")
            lines = [ln for ln in tail.splitlines() if ln.strip()]
            if not lines:
                return -1
            last = json.loads(lines[-1])
            return int(last.get("idx", -1))
        except Exception:
            return -1

    def append(
        self,
        *,
        entry_type: str,
        payload: Dict[str, Any],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> LedgerAppendResult:
        last = self._read_last_idx()
        idx = last + 1
        entry = {
            "schema_version": "evidence-ledger/0.1",
            "idx": idx,
            "entry_type": str(entry_type),
            "payload": payload or {},
            "provenance": provenance or {},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(canonical_json_dumps(entry) + "\n")
        return LedgerAppendResult(idx=idx, entry=entry)

    def read_tail(self, n: int = 1) -> List[Dict[str, Any]]:
        if n <= 0 or not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                lines = [ln for ln in f.read().splitlines() if ln.strip()]
            out = [json.loads(ln) for ln in lines[-n:]]
            return out
        except Exception:
            return []

    def tail_hash(self, n: int = 100) -> str:
        """
        Compute a deterministic hash of the last N entries for change detection.

        Args:
            n: Number of tail entries to hash (default 100)

        Returns:
            SHA256 hash of the canonical JSON representation of the tail
        """
        import hashlib

        tail = self.read_tail(n)
        if not tail:
            return hashlib.sha256(b"").hexdigest()

        # Use canonical JSON dumps for deterministic hashing
        tail_json = canonical_json_dumps(tail)
        return hashlib.sha256(tail_json.encode("utf-8")).hexdigest()

