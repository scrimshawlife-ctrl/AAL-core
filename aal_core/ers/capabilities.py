from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class CapabilityToken:
    """
    Minimal, deterministic capability token.
    In v0.1 this is an allowlist mapping module_id -> allowed capability strings.
    """
    module_id: str
    allowed: Set[str]


def can_apply(cap: CapabilityToken, required: str) -> bool:
    return required in cap.allowed


def default_capability_registry() -> Dict[str, CapabilityToken]:
    """
    Conservative defaults: empty.
    Modules should register explicitly.
    """
    return {}
