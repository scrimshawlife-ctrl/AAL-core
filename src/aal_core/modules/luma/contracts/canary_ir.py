from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class CanaryItem:
    proposal_id: str
    pattern_id: str
    base_patterns: List[str]
    semantic_dependencies: List[str]
    intended_gain: Dict[str, float]
    risks: Dict[str, Any]
    suggested_steps: List[str]


@dataclass(frozen=True)
class CanaryReport:
    schema: str
    scene_hash: str
    generated_utc: str
    items: List[CanaryItem]
    provenance: Dict[str, Any]
