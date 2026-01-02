from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .enums import ProposalStatus


@dataclass(frozen=True)
class PatternProposal:
    proposal_id: str
    base_patterns: List[str]
    pattern_spec: Dict[str, Any]
    justification: Dict[str, Any]
    scores: Dict[str, float]
    risks: Dict[str, Any]
    provenance: Dict[str, Any]
    status: str = ProposalStatus.PROPOSED.value
    notes: Optional[Dict[str, Any]] = None
