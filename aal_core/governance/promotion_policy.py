from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


def _canonical_json_dumps(obj: Any) -> str:
    """
    Deterministic JSON rendering (stable keys + no whitespace noise).
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _default_promotions_path() -> Path:
    # Allow explicit override for tests / embedding, but keep deterministic default.
    env = os.environ.get("AAL_PROMOTIONS_PATH", "").strip()
    if env:
        return Path(env)
    return Path(".aal") / "promotions.json"


@dataclass(frozen=True)
class PromotionPolicy:
    """
    Canonical promotions policy file loader/saver.

    v2.1 needs only:
    - `.items` list of dicts
    - revoked filtering via `revoked_at_idx`
    """

    items: List[Dict[str, Any]]
    schema_version: str = "promotions/0.1"

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PromotionPolicy":
        p = path or _default_promotions_path()
        if not p.exists():
            return cls(items=[])

        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            # Deterministic failure mode: treat as empty policy
            return cls(items=[])

        if isinstance(raw, list):
            items = raw
        else:
            items = raw.get("items", []) if isinstance(raw, dict) else []

        if not isinstance(items, list):
            items = []

        # Normalize to dicts only (drop non-dicts deterministically)
        norm: List[Dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                norm.append(it)
        return cls(items=norm, schema_version=str((raw or {}).get("schema_version", cls.schema_version)) if isinstance(raw, dict) else cls.schema_version)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": self.schema_version, "items": list(self.items)}
        path.write_text(_canonical_json_dumps(payload) + "\n", encoding="utf-8")

