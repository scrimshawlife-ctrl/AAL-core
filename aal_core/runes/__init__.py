"""
ABX-Runes provenance helpers (compat layer).
"""

from .attach import attach_runes, manifest_sha256, vendor_lock_sha256

__all__ = [
    "attach_runes",
    "manifest_sha256",
    "vendor_lock_sha256",
]

