"""
YGGDRASIL-IR: topology + governance metadata layer for AAL / ABX-Runes.

Tree = authority / governance spine.
DAG  = data dependency veins (depends_on).

This package is intentionally "metadata-first":
- It validates, plans, and renders.
- It does not execute rune logic.
"""

from .schema import (
    Realm,
    Lane,
    PromotionState,
    NodeKind,
    PortSpec,
    YggdrasilNode,
    RuneLink,
    YggdrasilManifest,
    PlanOptions,
    ExecutionPlan,
)
from .validate import validate_manifest, ValidationError
from .plan import build_execution_plan
from .render import render_tree_view, render_veins_view

__all__ = [
    "Realm",
    "Lane",
    "PromotionState",
    "NodeKind",
    "PortSpec",
    "YggdrasilNode",
    "RuneLink",
    "YggdrasilManifest",
    "PlanOptions",
    "ExecutionPlan",
    "validate_manifest",
    "ValidationError",
    "build_execution_plan",
    "render_tree_view",
    "render_veins_view",
]
