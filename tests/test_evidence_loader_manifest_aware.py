from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from abx_runes.yggdrasil.evidence_bundle import SCHEMA_VERSION, lock_hash
from abx_runes.yggdrasil.evidence_loader import load_evidence_bundles_for_manifest
from abx_runes.yggdrasil.linkgen import evidence_port_name
from abx_runes.yggdrasil.schema import (
    ProvenanceSpec, YggdrasilManifest, YggdrasilNode, RuneLink, NodeKind, Realm, Lane
)


def _prov():
    return ProvenanceSpec(schema_version="yggdrasil-ir/0.1", manifest_hash="x", created_at="t", updated_at="t", source_commit="c")


def test_manifest_aware_loader_rejects_nonexistent_bridge():
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="hel.det", kind=NodeKind.RUNE, realm=Realm.HEL, lane=Lane.SHADOW, authority_level=50, parent=None),
            YggdrasilNode(id="asg.pred", kind=NodeKind.RUNE, realm=Realm.ASGARD, lane=Lane.FORECAST, authority_level=50, parent=None),
        ),
        links=(RuneLink(id="link1", from_node="hel.det", to_node="asg.pred", allowed_lanes=("shadow->forecast",), evidence_required=("EXPLICIT_SHADOW_FORECAST_BRIDGE",), required_evidence_ports=()),),
    )

    with TemporaryDirectory() as td:
        p = Path(td) / "b.json"
        bundle = {
            "schema_version": SCHEMA_VERSION,
            "created_at": "2025-12-31T00:00:00+00:00",
            "bundle_hash": "",
            "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
            "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
            "calibration_refs": [],
            "bridges": [{"from": "hel.det", "to": "asg.pred"}, {"from": "nope", "to": "missing"}]
        }
        p.write_text(json.dumps(lock_hash(bundle)), encoding="utf-8")

        res = load_evidence_bundles_for_manifest([str(p)], m)
        # valid edge should be present
        assert evidence_port_name("hel.det", "asg.pred") in res.input_bundle.present
        # invalid edge should be recorded as bad
        assert any("bridge_not_in_manifest:nope->missing" in x["reason"] for x in res.bundle_paths_bad)
