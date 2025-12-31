from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_json_dumps(obj: Any) -> str:
    """
    Deterministic JSON serialization:
    - sorted keys
    - stable separators
    - UTF-8 safe
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def hash_manifest_dict(manifest: Dict[str, Any]) -> str:
    """
    Hash manifest content excluding provenance.manifest_hash (self-hash-safe).
    """
    m = json.loads(canonical_json_dumps(manifest))  # deep copy
    prov = m.get("provenance", {})
    prov["manifest_hash"] = ""
    m["provenance"] = prov
    return _sha256_hex(canonical_json_dumps(m))
