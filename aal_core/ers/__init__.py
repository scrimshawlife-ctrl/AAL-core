"""
ERS (Evidence-Based Runtime Stabilization)
Tuning plane hot-apply logic with capability gating and stabilization windows.
"""

from .capabilities import CapabilityToken, can_apply, default_capability_registry
from .stabilization import (
    StabilizationState,
    allowed_by_stabilization,
    new_state,
    note_change,
    tick_cycle,
)
from .tuning_apply import HotApplyResult, hot_apply_tuning_ir
from .portfolio_apply import PortfolioApplyResult, apply_portfolio_tuning_ir

__all__ = [
    "CapabilityToken",
    "can_apply",
    "default_capability_registry",
    "StabilizationState",
    "allowed_by_stabilization",
    "new_state",
    "note_change",
    "tick_cycle",
    "HotApplyResult",
    "hot_apply_tuning_ir",
    "PortfolioApplyResult",
    "apply_portfolio_tuning_ir",
]
