from __future__ import annotations

import json

from abx_runes.yggdrasil.hashing import canonical_json_dumps, sha256_hex
from abx_runes.yggdrasil.io import verify_hash


def _relock_like_script(m: dict) -> dict:
    mm = json.loads(canonical_json_dumps(m))
    mm["provenance"]["manifest_hash"] = ""
    h = sha256_hex(canonical_json_dumps(mm).encode("utf-8"))
    mm["provenance"]["manifest_hash"] = h
    return mm


def test_bridge_apply_semantics_minimal():
    manifest = {
        "provenance": {"schema_version": "yggdrasil-ir/0.1", "manifest_hash": "", "created_at": "t", "updated_at": "t", "source_commit": "c"},
        "nodes": [],
        "links": [
            {"id": "link.aaaa", "from_node": "hel.det", "to_node": "asg.pred", "allowed_lanes": [], "evidence_required": [], "required_evidence_ports": []}
        ],
    }
    manifest = _relock_like_script(manifest)
    assert verify_hash(manifest) is True

    patch = {
        "id": "link.aaaa",
        "from_node": "hel.det",
        "to_node": "asg.pred",
        "allowed_lanes": ["shadow->forecast"],
        "evidence_required": ["EXPLICIT_SHADOW_FORECAST_BRIDGE"],
        "required_evidence_ports": [{"name": "evidence.link.aaaa", "dtype": "evidence_bundle", "required": True}],
    }

    # Apply inline using the same core functions as the script
    from abx_runes.yggdrasil.bridge_apply_core import apply_patch_to_link, relock_manifest_hash, find_link_index
    idx = find_link_index(manifest, patch)
    manifest["links"][idx] = apply_patch_to_link(manifest["links"][idx], patch)
    manifest2 = relock_manifest_hash(manifest)
    assert verify_hash(manifest2) is True
    assert manifest2["links"][0]["allowed_lanes"] == ["shadow->forecast"]
