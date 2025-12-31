"""
AAL Overlay Adapter Layer.

Hot-swappable overlay system for ABX-Runes memory governance.
Provides registry, runners, dispatch, and provenance tracking.
"""

from .dispatch import dispatch_capability_call, make_overlay_run_job, get_memory_profile
from .manifest import OverlayManifest, Capability
from .provenance import create_provenance_record, ProvenanceRecord
from .registry import OverlayRegistry

__all__ = [
    "dispatch_capability_call",
    "make_overlay_run_job",
    "get_memory_profile",
    "OverlayManifest",
    "Capability",
    "OverlayRegistry",
    "create_provenance_record",
    "ProvenanceRecord",
]

__version__ = "0.1.0"
