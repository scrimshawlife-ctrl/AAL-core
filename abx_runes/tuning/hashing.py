from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_json_dumps(d: Dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def content_hash(obj: Dict[str, Any], blank_fields: tuple[str, ...] = ()) -> str:
    """
    Deterministic hash of a dict after blanking specified fields.
    """
    o = json.loads(canonical_json_dumps(obj))
    for f in blank_fields:
        if f in o:
            o[f] = ""
    return sha256_hex(canonical_json_dumps(o).encode("utf-8"))
