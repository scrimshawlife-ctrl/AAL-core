from __future__ import annotations

from typing import Any, Dict

from abx_runes.tuning.emit import canonical_write
from abx_runes.tuning.hashing import content_hash


def lock_portfolio_tuning_ir(ir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically compute portfolio_hash with portfolio_hash blanked.
    """
    d = dict(ir)
    d["portfolio_hash"] = ""
    h = content_hash(d, blank_fields=())
    out = dict(d)
    out["portfolio_hash"] = h
    return out


__all__ = [
    "canonical_write",
    "lock_portfolio_tuning_ir",
]

