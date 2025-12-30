from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from .hash import canonical_json_dumps, hash_manifest_dict


def load_manifest_dict(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest_dict(path: Path, manifest: Dict[str, Any]) -> None:
    path.write_text(canonical_json_dumps(manifest) + "\n", encoding="utf-8")


def recompute_and_lock_hash(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a new dict with provenance.manifest_hash set deterministically.
    """
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
    actual = hash_manifest_dict(manifest)
    return actual == expected
