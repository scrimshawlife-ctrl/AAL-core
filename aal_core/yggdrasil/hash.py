from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_json_dumps(obj: Any) -> str:
    """
    Deterministic JSON serialization:
    - sorted keys
    - no whitespace variance
    - UTF-8 safe
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_manifest_dict(manifest: Dict[str, Any]) -> str:
    """
    Hash the manifest content *excluding* provenance.manifest_hash itself,
    so we can set it deterministically.

    This prevents self-referential hashing.
    """
    m = json.loads(canonical_json_dumps(manifest))  # deep-copy via canonicalization
    prov = m.get("provenance", {})
    prov["manifest_hash"] = ""  # blank it before hashing
    m["provenance"] = prov
    return sha256_hex(canonical_json_dumps(m))
