from __future__ import annotations

from typing import Any, Dict, List

from abx_runes.tuning.hashing import content_hash


def lock_portfolio_ir(ir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically compute ir_hash with ir_hash blanked.
    """
    d = dict(ir)
    d["ir_hash"] = ""
    h = content_hash(d, blank_fields=())
    out = dict(d)
    out["ir_hash"] = h
    return out


def make_portfolio_ir(
    *,
    source_cycle_id: str,
    items: List[Dict[str, Any]],
    notes: Dict[str, Any],
) -> Dict[str, Any]:
    return lock_portfolio_ir(
        {
            "schema_version": "portfolio-tuning-ir/0.1",
            "ir_hash": "",
            "source_cycle_id": source_cycle_id,
            "items": list(items),
            "notes": dict(notes),
        }
    )

