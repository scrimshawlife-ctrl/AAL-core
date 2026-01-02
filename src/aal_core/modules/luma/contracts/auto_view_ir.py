from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class AutoViewPlan:
    schema: str
    scene_hash: str
    view_id: str
    primitives: List[str]
    layout: Dict[str, Any]
    channels: Dict[str, str]
    mappings: List[Dict[str, Any]]
    scores: Dict[str, float]
    reasons: Dict[str, Any]
    warnings: List[str]
    provenance: Dict[str, Any]
    limits: Dict[str, Any]
