"""
AAL-Core Rune Provenance Helpers
=================================

Utilities for attaching ABX-Runes provenance metadata to bus payloads.

All functions compute deterministic SHA256 hashes of vendored assets:
- LOCK.json (vendor integrity)
- manifest.json (sigil registry)

No network calls. Stdlib only. Deterministic.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "abx_runes"


def _sha256_hex(b: bytes) -> str:
    """Compute SHA256 hex digest of bytes."""
    return hashlib.sha256(b).hexdigest()


def load_vendor_lock() -> Dict[str, Any]:
    """
    Load vendor LOCK.json.

    Returns:
        Dict containing lock metadata, file hashes, version info.

    Raises:
        FileNotFoundError: If LOCK.json doesn't exist.
    """
    lock_path = VENDOR_ROOT / "LOCK.json"
    if not lock_path.exists():
        raise FileNotFoundError(f"Vendor LOCK.json not found at {lock_path}")
    return json.loads(lock_path.read_text(encoding="utf-8"))


def vendor_lock_sha256() -> str:
    """
    Compute SHA256 hash of vendor LOCK.json bytes.

    Returns:
        Hex string SHA256 digest.

    Raises:
        FileNotFoundError: If LOCK.json doesn't exist.
    """
    lock_path = VENDOR_ROOT / "LOCK.json"
    if not lock_path.exists():
        raise FileNotFoundError(f"Vendor LOCK.json not found at {lock_path}")
    return _sha256_hex(lock_path.read_bytes())


def manifest_sha256() -> str:
    """
    Compute SHA256 hash of vendored sigils/manifest.json.

    Returns:
        Hex string SHA256 digest.

    Raises:
        FileNotFoundError: If manifest.json doesn't exist.
    """
    manifest_path = VENDOR_ROOT / "sigils" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    return _sha256_hex(manifest_path.read_bytes())


def attach_runes(
    payload: Dict[str, Any],
    used: List[str],
    gate_state: str,
    extras: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Attach ABX-Runes provenance metadata to payload.

    Creates a shallow copy of the payload and adds "abx_runes" field with:
    - used: List of rune IDs consumed
    - gate_state: Current gate state (e.g., "OPEN", "CLEAR", "SEAL")
    - manifest_sha256: Hash of sigils/manifest.json
    - vendor_lock_sha256: Hash of vendor LOCK.json
    - Any additional fields from extras dict

    Args:
        payload: Original payload dict (not mutated).
        used: List of rune IDs referenced in this payload.
        gate_state: Current gate state string.
        extras: Optional dict of additional metadata to include.

    Returns:
        New dict with payload contents + abx_runes metadata.

    Raises:
        FileNotFoundError: If vendor assets don't exist.
    """
    result = payload.copy()  # Shallow copy - do not mutate original

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
