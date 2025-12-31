"""
AAL-Core Rune Provenance Helpers (compat)

This mirrors the src-tree implementation so `import aal_core.runes.attach`
works regardless of sys.path order during tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "abx_runes"


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_vendor_lock() -> Dict[str, Any]:
    lock_path = VENDOR_ROOT / "LOCK.json"
    if not lock_path.exists():
        raise FileNotFoundError(f"Vendor LOCK.json not found at {lock_path}")
    return json.loads(lock_path.read_text(encoding="utf-8"))


def vendor_lock_sha256() -> str:
    lock_path = VENDOR_ROOT / "LOCK.json"
    if not lock_path.exists():
        raise FileNotFoundError(f"Vendor LOCK.json not found at {lock_path}")
    return _sha256_hex(lock_path.read_bytes())


def manifest_sha256() -> str:
    manifest_path = VENDOR_ROOT / "sigils" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    return _sha256_hex(manifest_path.read_bytes())


def attach_runes(
    payload: Dict[str, Any],
    used: List[str],
    gate_state: str,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result = payload.copy()
    rune_metadata = {
        "used": used,
        "gate_state": gate_state,
        "manifest_sha256": manifest_sha256(),
        "vendor_lock_sha256": vendor_lock_sha256(),
    }
    if extras:
        rune_metadata.update(extras)
    result["abx_runes"] = rune_metadata
    return result

