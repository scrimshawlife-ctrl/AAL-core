from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import json

from abx_runes.tuning.hashing import canonical_json_dumps


DEFAULT_PATH = Path(".aal/safe_sets.json")


def safe_set_key(*, module_id: str, knob: str, baseline_signature: Dict[str, str]) -> str:
    base_key = ",".join(f"{k}={baseline_signature[k]}" for k in sorted(baseline_signature))
    return f"{module_id}::{knob}::{base_key}"


@dataclass(frozen=True)
class SafeSetEntry:
    set_idx: int
    until_idx: int
    kind: str  # "enum" | "numeric"
    safe_values: Optional[list]
    safe_min: Optional[float]
    safe_max: Optional[float]
    support: Dict[str, Any]
    provenance: Dict[str, Any]


class SafeSetStore:
    def __init__(self, entries: Dict[str, Dict[str, Any]] | None = None):
        self.entries = entries or {}

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "SafeSetStore":
        if not path.exists():
            return cls(entries={})
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return cls(entries=d.get("entries") or {})
        except Exception:
            return cls(entries={})

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": "safe-set-store/0.1", "entries": self.entries}
        path.write_text(canonical_json_dumps(payload) + "\n", encoding="utf-8")

    def get(self, key: str, now_idx: int) -> Optional[Dict[str, Any]]:
        e = self.entries.get(key)
        if not e:
            return None
        if int(now_idx) >= int(e.get("until_idx", 0)):
            return None
        return e

    def set(self, key: str, entry: SafeSetEntry) -> None:
        self.entries[key] = {
            "schema_version": "safe-set-entry/0.1",
            "set_idx": int(entry.set_idx),
            "until_idx": int(entry.until_idx),
            "kind": str(entry.kind),
            "safe_values": entry.safe_values,
            "safe_min": entry.safe_min,
            "safe_max": entry.safe_max,
            "support": dict(entry.support or {}),
            "provenance": dict(entry.provenance or {}),
        }

    def prune_expired(self, now_idx: int) -> int:
        dead = []
        for k, e in self.entries.items():
            if int(now_idx) >= int(e.get("until_idx", 0)):
                dead.append(k)
        for k in dead:
            del self.entries[k]
        return len(dead)

