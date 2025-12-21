"""
AAL-Core Bus Frame Construction
================================

Factory functions for creating canon-aligned ResonanceFrame messages.

All frames carry:
- UTC timestamp
- Module identifier
- Payload data
- ABX-Runes metadata (optional)
- Deterministic provenance hashes (vendor_lock + manifest)

No network calls. Stdlib only. Deterministic.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..schema.resonance_frame import ResonanceFrame
from ..runes.attach import vendor_lock_sha256, manifest_sha256


def make_frame(
    module: str,
    payload: Dict[str, Any],
    *,
    abx_runes: Optional[Dict[str, Any]] = None
) -> ResonanceFrame:
    """
    Construct a ResonanceFrame with automatic provenance injection.

    Automatically injects vendor_lock_sha256 and manifest_sha256 if vendor exists.
    If vendor assets are missing, provenance will be empty (graceful degradation).

    Args:
        module: Source module identifier (e.g., "abraxas.overlay").
        payload: Message payload data.
        abx_runes: Optional ABX-Runes metadata to include in frame.

    Returns:
        ResonanceFrame with UTC timestamp, module, payload, abx_runes, and provenance.

    Example:
        >>> frame = make_frame("abraxas.overlay", {"phase": "OPEN", "data": {...}})
        >>> frame["provenance"]["vendor_lock_sha256"]
        'a3f5...'
    """
    frame: ResonanceFrame = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "module": module,
        "payload": payload,
        "abx_runes": abx_runes,
        "provenance": {},
    }

    # Inject provenance hashes if vendor exists
    try:
        frame["provenance"]["vendor_lock_sha256"] = vendor_lock_sha256()
        frame["provenance"]["manifest_sha256"] = manifest_sha256()
    except FileNotFoundError:
        # Vendor not present - graceful degradation
        # Frame still valid but without rune provenance
        pass

    return frame
