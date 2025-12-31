from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .hashing import canonical_json_dumps, hash_manifest_dict


def load_manifest_dict(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest_dict(path: Path, manifest: Dict[str, Any]) -> None:
    path.write_text(canonical_json_dumps(manifest) + "\n", encoding="utf-8")


def recompute_and_lock_hash(manifest: Dict[str, Any]) -> Dict[str, Any]:
    m = json.loads(canonical_json_dumps(manifest))
    prov = m.setdefault("provenance", {})
    prov["manifest_hash"] = hash_manifest_dict(m)
    m["provenance"] = prov
    return m


def verify_hash(manifest: Dict[str, Any]) -> bool:
    prov = manifest.get("provenance", {})
    expected = str(prov.get("manifest_hash", ""))
    if not expected:
        return False
    return hash_manifest_dict(manifest) == expected
