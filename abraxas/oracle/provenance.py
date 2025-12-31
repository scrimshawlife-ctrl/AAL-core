"""Oracle provenance stamping with ABX-Runes manifest verification.

Provides manifest hashing and output stamping for oracle provenance tracking.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List


def load_manifest_sha256() -> str:
    """
    Load the ABX-Runes manifest and return its SHA256 hash.

    Returns:
        Hex-encoded SHA256 hash of manifest.json bytes

    Raises:
        FileNotFoundError: If manifest.json does not exist
    """
    manifest_path = Path(__file__).parent.parent / "runes" / "sigils" / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    manifest_bytes = manifest_path.read_bytes()
    return hashlib.sha256(manifest_bytes).hexdigest()


def stamp(
    output: Dict[str, Any],
    runes_used: List[str],
    gate_state: str,
    extras: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add ABX-Runes provenance stamp to oracle output.

    Args:
        output: Oracle output dictionary to stamp (modified in place)
        runes_used: List of rune IDs that were applied (e.g., ["ϟ₁", "ϟ₂", "ϟ₄"])
        gate_state: Current gate state from SDS ("CLOSED", "LIMINAL", "OPEN")
        extras: Additional provenance data to include

    Returns:
        Modified output dictionary with "abx_runes" section added

    The stamped section includes:
        - used: List of rune IDs applied
        - manifest_sha256: Hash of the runes manifest
        - gate_state: Current SDS gate state
        - All key-value pairs from extras
    """
    manifest_hash = load_manifest_sha256()

    output["abx_runes"] = {
        "used": runes_used,
        "manifest_sha256": manifest_hash,
        "gate_state": gate_state,
        **extras
    }

    return output
