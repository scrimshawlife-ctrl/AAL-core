"""
AAL-Core ABX-Runes Runtime Accessor
====================================

Provides read-only access to vendored ABX-Runes assets with lock verification.

Functions:
- list_runes() -> List of all runes from registry
- get_rune(id) -> Rune metadata by ID
- get_sigil_svg(id) -> SVG content for rune sigil
- verify_lock() -> Verify vendor integrity

All reads verify LOCK.json integrity before accessing assets.
No network calls. Stdlib only. Deterministic.
"""

from __future__ import annotations
from pathlib import Path
import json
import hashlib
from typing import Any, Dict, List


VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "abx_runes"


def _sha256_hex(b: bytes) -> str:
    """Compute SHA256 hex digest of bytes."""
    return hashlib.sha256(b).hexdigest()


def verify_lock() -> Dict[str, Any]:
    """
    Verify vendor LOCK.json integrity.

    Checks that all files listed in LOCK.json exist and match their SHA256 hashes.

    Returns:
        Dict with {"ok": True, "abx_runes_version": <version>}.

    Raises:
        FileNotFoundError: If LOCK.json or vendored files are missing.
        ValueError: If hash mismatches are detected.
    """
    lock = VENDOR_ROOT / "LOCK.json"
    if not lock.exists():
        raise FileNotFoundError(f"Missing LOCK.json at {lock}")

    data = json.loads(lock.read_text(encoding="utf-8"))

    for f in data["files"]:
        p = VENDOR_ROOT / f["path"]
        if not p.exists():
            raise FileNotFoundError(f"Missing vendored file: {p}")
        if _sha256_hex(p.read_bytes()) != f["sha256"]:
            raise ValueError(f"Hash mismatch for {f['path']}")

    return {"ok": True, "abx_runes_version": data.get("abx_runes_version")}


def _registry() -> Dict[str, Any]:
    """
    Load vendored registry.json after verifying lock.

    Returns:
        Registry data dict.
    """
    verify_lock()
    reg = VENDOR_ROOT / "registry.json"
    return json.loads(reg.read_text(encoding="utf-8"))


def list_runes() -> List[Dict[str, Any]]:
    """
    List all vendored runes.

    Returns:
        List of rune metadata dicts from registry.

    Raises:
        FileNotFoundError: If vendor assets missing.
        ValueError: If lock verification fails.
    """
    return _registry()["runes"]


def get_rune(rune_id: str) -> Dict[str, Any]:
    """
    Get rune metadata by ID.

    Args:
        rune_id: Rune identifier (e.g., "0001", "0042").

    Returns:
        Rune metadata dict.

    Raises:
        KeyError: If rune ID not found.
        FileNotFoundError: If vendor assets missing.
        ValueError: If lock verification fails.
    """
    for r in list_runes():
        if r["id"] == rune_id:
            return r
    raise KeyError(f"Unknown rune id: {rune_id}")


def get_sigil_svg(rune_id: str) -> str:
    """
    Get SVG content for rune sigil.

    Args:
        rune_id: Rune identifier.

    Returns:
        SVG file contents as string.

    Raises:
        KeyError: If rune ID not found.
        FileNotFoundError: If sigil SVG missing.
        ValueError: If lock verification fails.
    """
    r = get_rune(rune_id)
    fn = f'{r["id"]}_{r["short_name"]}.svg'
    p = VENDOR_ROOT / "sigils" / fn
    return p.read_text(encoding="utf-8")
