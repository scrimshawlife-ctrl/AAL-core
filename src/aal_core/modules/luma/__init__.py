"""
Canonical visualization projection layer for AAL / Abraxas symbolic state.

Key law: visualization is a deterministic projection of existing symbolic state.
It MUST NOT influence analysis or prediction.
"""

from .contracts.auto_view_ir import AutoViewPlan
from .governance.canary_runner import CanaryRunner
from .governance.ledger import ledger_status, load_ledger
from .governance.ops import accept_for_canary, add_note, record_exported_proposals, reject
from .ideation.auto_lens import AutoLens, AutoLensConfig
from .ideation.proposer import PatternProposer, ProposerConfig
from .pipeline.export import export_artifact, render
from .pipeline.export_auto_view import export_auto_view_plan
from .pipeline.export_canary_report import export_canary_report
from .pipeline.export_proposals import export_proposals
from .pipeline.export_scene import export_scene_ir
from .renderers.svg_static import SvgRenderConfig, SvgStaticRenderer

__all__ = [
    "render",
    "export_scene_ir",
    "export_artifact",
    "PatternProposer",
    "ProposerConfig",
    "export_proposals",
    "load_ledger",
    "ledger_status",
    "record_exported_proposals",
    "accept_for_canary",
    "reject",
    "add_note",
    "CanaryRunner",
    "export_canary_report",
    "AutoViewPlan",
    "AutoLens",
    "AutoLensConfig",
    "export_auto_view_plan",
    "SvgStaticRenderer",
    "SvgRenderConfig",
]
