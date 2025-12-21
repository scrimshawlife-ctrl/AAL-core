"""
AAL-Core ResonanceFrame Schema
===============================

Canon-aligned frame schema for bus payloads with embedded ABX-Runes provenance.

ResonanceFrame wraps all bus messages with:
- UTC timestamp
- Module identifier
- Payload data
- ABX-Runes metadata (optional)
- Provenance hashes (vendor lock + manifest)

All frames carry deterministic provenance anchors ensuring reproducibility.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TypedDict


class ResonanceFrame(TypedDict, total=False):
    """
    Canon-aligned bus message frame with embedded rune provenance.

    Fields:
        utc: ISO 8601 UTC timestamp of frame creation
        module: Source module identifier (e.g., "abraxas.overlay", "aal_core.scheduler")
        payload: Actual message data (dict)
        abx_runes: ABX-Runes metadata including used runes, gate state, provenance hashes
        provenance: Vendor lock and manifest SHA256 hashes for reproducibility
    """
    utc: str
    module: str
    payload: Dict[str, Any]
    abx_runes: Optional[Dict[str, Any]]
    provenance: Dict[str, Any]  # Must include: vendor_lock_sha256, manifest_sha256 (if available)


# Type alias for convenience
Frame = ResonanceFrame
