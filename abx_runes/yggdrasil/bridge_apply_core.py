from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from .hashing import canonical_json_dumps, sha256_hex


ALLOWED_PATCH_FIELDS = {"allowed_lanes", "evidence_required", "required_evidence_ports"}


def find_link_index(manifest: Dict[str, Any], patch: Dict[str, Any]) -> int:
    links = manifest.get("links", []) or []
    pid = patch.get("id", "")
    frm = patch.get("from_node", "")
    to = patch.get("to_node", "")

    matches = []
    for i, l in enumerate(links):
        if pid and str(l.get("id", "")) == str(pid):
            matches.append(i)
            continue
        if frm and to and str(l.get("from_node", "")) == str(frm) and str(l.get("to_node", "")) == str(to):
            matches.append(i)

    if len(matches) == 0:
        raise ValueError("No matching link found for patch (by id or from_node/to_node).")
    if len(matches) > 1:
        raise ValueError("Ambiguous patch: multiple matching links found.")
    return matches[0]


def apply_patch_to_link(link: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(link)
    for k in sorted(ALLOWED_PATCH_FIELDS):
        if k in patch:
            out[k] = patch[k]
    return out


def relock_manifest_hash(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Self-hash safe: set provenance.manifest_hash="" during hashing, then fill it.
    """
    m = json.loads(canonical_json_dumps(manifest))
    prov = m.get("provenance", {})
    if not isinstance(prov, dict):
        prov = {}
    prov["manifest_hash"] = ""
    m["provenance"] = prov
    payload = canonical_json_dumps(m).encode("utf-8")
    h = sha256_hex(payload)
    m["provenance"]["manifest_hash"] = h
    return m


def validate_patch_fields(patch: Dict[str, Any]) -> Tuple[bool, str]:
    unknown = set(patch.keys()) - (ALLOWED_PATCH_FIELDS | {"id", "from_node", "to_node"})
    if unknown:
        return False, f"unknown_fields:{sorted(unknown)}"
    return True, "ok"
