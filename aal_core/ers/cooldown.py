from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from abx_runes.tuning.hashing import canonical_json_dumps

DEFAULT_PATH = Path(".aal/cooldowns.json")


def _baseline_items(baseline_sig: Dict[str, str]) -> str:
    # Stable ordering ensures determinism regardless of dict insertion order.
    return ",".join(f"{k}={baseline_sig[k]}" for k in sorted(baseline_sig))


def cooldown_key(*, module_id: str, knob: str, value: Any, baseline_signature: Dict[str, str]) -> str:
    """
    Deterministic key:
      module::knob::value::baseline_items
    """
    return f"{module_id}::{knob}::{str(value)}::{_baseline_items(baseline_signature)}"


@dataclass(frozen=True)
class CooldownEntry:
    set_idx: int
    until_idx: int
    reason: str
    stats_snapshot: Dict[str, Any]


class CooldownStore:
    def __init__(self, entries: Optional[Dict[str, Dict[str, Any]]] = None):
        self.entries: Dict[str, Dict[str, Any]] = entries or {}

    def to_jsonable(self) -> Dict[str, Any]:
        return {"schema_version": "cooldown-store/0.1", "entries": self.entries}

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "CooldownStore":
        if not path.exists():
            return cls(entries={})
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return cls(entries=d.get("entries") or {})
        except Exception:
            # Corrupt file should not brick runtime; treat as empty.
            return cls(entries={})

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json_dumps(self.to_jsonable()) + "\n", encoding="utf-8")

    def set(self, key: str, entry: CooldownEntry) -> None:
        self.entries[key] = {
            "set_idx": int(entry.set_idx),
            "until_idx": int(entry.until_idx),
            "reason": str(entry.reason),
            "stats_snapshot": dict(entry.stats_snapshot or {}),
        }

    def is_active(self, key: str, now_idx: int) -> bool:
        e = self.entries.get(key)
        if not e:
            return False
        return int(now_idx) < int(e.get("until_idx", 0))

    def prune_expired(self, now_idx: int) -> int:
        dead = [k for k, e in self.entries.items() if int(now_idx) >= int(e.get("until_idx", 0))]
        for k in dead:
            del self.entries[k]
        return len(dead)


def set_cooldown(
    *,
    store: CooldownStore,
    module_id: str,
    knob: str,
    value: Any,
    baseline_signature: Dict[str, str],
    now_idx: int,
    cooldown_cycles: int,
    reason: str,
    stats_snapshot: Optional[Dict[str, Any]] = None,
) -> str:
    key = cooldown_key(module_id=module_id, knob=knob, value=value, baseline_signature=baseline_signature)
    store.set(
        key,
        CooldownEntry(
            set_idx=int(now_idx),
            until_idx=int(now_idx) + int(cooldown_cycles),
            reason=str(reason),
            stats_snapshot=dict(stats_snapshot or {}),
        ),
    )
    return key


def is_cooled_down(*, store: CooldownStore, key: str, now_idx: int) -> bool:
    return store.is_active(key, now_idx)


def prune_expired(*, store: CooldownStore, now_idx: int) -> int:
    return store.prune_expired(now_idx)

