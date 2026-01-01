from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from abx_runes.tuning.hashing import canonical_json_dumps


DEFAULT_PATH = Path(".aal/promotions.json")


def _key(item: Dict[str, Any]) -> Tuple[str, str, str, str]:
    base = item.get("baseline_signature") or {}
    base_key = ",".join(f"{k}={base[k]}" for k in sorted(base))
    return (
        str(item.get("module_id", "")),
        str(item.get("knob", "")),
        str(item.get("value", "")),
        base_key,
    )


class PromotionPolicy:
    def __init__(self, items: List[Dict[str, Any]] | None = None):
        self.items = items or []

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "PromotionPolicy":
        if not path.exists():
            return cls(items=[])
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return cls(items=d.get("items") or [])
        except Exception:
            return cls(items=[])

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "promotion-policy/0.1",
            "items": sorted(self.items, key=_key),
        }
        path.write_text(canonical_json_dumps(payload) + "\n", encoding="utf-8")

    def upsert(self, item: Dict[str, Any]) -> None:
        k = _key(item)
        out: List[Dict[str, Any]] = []
        replaced = False
        for it in self.items:
            if _key(it) == k:
                out.append(item)
                replaced = True
            else:
                out.append(it)
        if not replaced:
            out.append(item)
        self.items = out

    def revoke(
        self,
        *,
        module_id: str,
        knob: str,
        value: Any,
        baseline_signature: Dict[str, str],
        revoked_at_idx: int,
    ) -> bool:
        base_key = ",".join(f"{k}={baseline_signature[k]}" for k in sorted(baseline_signature))
        k = (str(module_id), str(knob), str(value), base_key)
        changed = False
        out: List[Dict[str, Any]] = []
        for it in self.items:
            if _key(it) == k:
                it2 = dict(it)
                it2["revoked_at_idx"] = int(revoked_at_idx)
                out.append(it2)
                changed = True
            else:
                out.append(it)
        self.items = out
        return changed

