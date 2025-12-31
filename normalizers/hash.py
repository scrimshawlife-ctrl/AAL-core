"""
Stable hashing utilities for normalizer configurations.
"""
import json
import hashlib
from typing import Dict, Any


def stable_hash_dict(d: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA256 hash of a dictionary.

    Uses stable JSON serialization with sorted keys and
    compact separators to ensure identical hashes across runs.

    Args:
        d: Dictionary to hash

    Returns:
        SHA256 hex digest (64 characters)
    """
    canonical = json.dumps(
        d,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
