from __future__ import annotations

from typing import Any, Dict, Tuple

from .hashing import content_hash, canonical_json_dumps


def lock_tuning_ir(ir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically compute ir_hash with ir_hash blanked.
    """
    d = dict(ir)
    d["ir_hash"] = ""
    h = content_hash(d, blank_fields=())
    out = dict(d)
    out["ir_hash"] = h
    return out


def canonical_write(path: str, d: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(canonical_json_dumps(d) + "\n")
