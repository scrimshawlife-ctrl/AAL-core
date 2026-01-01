"""
AAL-Core Bus Frame Construction (compat)

Kept in the root `aal_core` package so imports work regardless of whether tests
prepend `/workspace/src` to `sys.path`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..schema.resonance_frame import ResonanceFrame
from ..runes.attach import manifest_sha256, vendor_lock_sha256


def make_frame(
    module: str,
    payload: Dict[str, Any],
    *,
    abx_runes: Optional[Dict[str, Any]] = None,
) -> ResonanceFrame:
    frame: ResonanceFrame = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "module": module,
        "payload": payload,
        "abx_runes": abx_runes,
        "provenance": {},
    }

    # Inject provenance hashes if vendor exists (graceful degradation).
    try:
        frame["provenance"]["vendor_lock_sha256"] = vendor_lock_sha256()
        frame["provenance"]["manifest_sha256"] = manifest_sha256()
    except FileNotFoundError:
        pass

    return frame

