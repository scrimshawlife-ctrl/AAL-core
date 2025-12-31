from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from .hashing import canonical_json_dumps


SCHEMA_VERSION = "abx-evidence-bundle/0.1"


def hash_bundle(bundle: Dict[str, Any]) -> str:
    """
    Self-hash safe: set bundle_hash="" while hashing.
    """
    b = json.loads(canonical_json_dumps(bundle))  # deep copy
    b["bundle_hash"] = ""
    payload = canonical_json_dumps(b).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def lock_hash(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute and set bundle_hash in the bundle.
    """
    b = json.loads(canonical_json_dumps(bundle))
    b["bundle_hash"] = hash_bundle(b)
    return b


def verify_hash(bundle: Dict[str, Any]) -> bool:
    """
    Verify bundle_hash matches computed hash.
    """
    expected = str(bundle.get("bundle_hash", ""))
    if not expected:
        return False
    return expected == hash_bundle(bundle)


def minimal_validate(bundle: Dict[str, Any]) -> None:
    """
    Minimal deterministic validation (no external deps).
    """
    if not isinstance(bundle, dict):
        raise ValueError("Bundle must be an object.")
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(bundle.get("sources", None), list):
        raise ValueError("sources must be an array.")
    if not isinstance(bundle.get("claims", None), list):
        raise ValueError("claims must be an array.")
