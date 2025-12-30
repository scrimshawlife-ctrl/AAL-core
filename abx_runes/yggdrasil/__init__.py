"""
YGGDRASIL-IR (ABX-Runes): topology + governance metadata layer.

Tree = authority / governance spine.
DAG  = data dependency veins (depends_on).

This package is intentionally metadata-first:
- validates, plans, and renders topologies
- does not execute runes
"""

from .schema import (
    Realm,
    Lane,
    PromotionState,
    NodeKind,
    PortSpec,
    StabilizationSpec,
    GovernanceSpec,
    ProvenanceSpec,
    YggdrasilNode,
    RuneLink,
    YggdrasilManifest,
    PlanOptions,
    ExecutionPlan,
)
from .validate import validate_manifest, ValidationError
from .plan import build_execution_plan
from .render import render_tree_view, render_veins_view, render_plan
from .hashing import canonical_json_dumps, hash_manifest_dict
from .io import load_manifest_dict, save_manifest_dict, recompute_and_lock_hash, verify_hash
from .emitter_real import RealEmitterConfig, emit_manifest_from_repo
from .overlay_introspect import OverlayRuneDecl, load_overlay_manifest_json, extract_declared_runes
from .linkgen import stable_edge_id, lane_pair, ensure_links_for_crossings
from .lint import render_forbidden_crossings_report

__all__ = [
    "Realm",
    "Lane",
    "PromotionState",
    "NodeKind",
    "PortSpec",
    "StabilizationSpec",
    "GovernanceSpec",
    "ProvenanceSpec",
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
    "render_plan",
    "canonical_json_dumps",
    "hash_manifest_dict",
    "load_manifest_dict",
    "save_manifest_dict",
    "recompute_and_lock_hash",
    "verify_hash",
    "RealEmitterConfig",
    "emit_manifest_from_repo",
    "OverlayRuneDecl",
    "load_overlay_manifest_json",
    "extract_declared_runes",
    "stable_edge_id",
    "lane_pair",
    "ensure_links_for_crossings",
    "render_forbidden_crossings_report",
]
