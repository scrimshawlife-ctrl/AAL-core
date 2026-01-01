"""
AAL-Core ResonanceFrame Schema (compat)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict


class ResonanceFrame(TypedDict, total=False):
    utc: str
    module: str
    payload: Dict[str, Any]
    abx_runes: Optional[Dict[str, Any]]
    provenance: Dict[str, Any]


Frame = ResonanceFrame

