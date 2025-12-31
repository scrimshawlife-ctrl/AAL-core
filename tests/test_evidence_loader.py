from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from abx_runes.yggdrasil.evidence_bundle import SCHEMA_VERSION, lock_hash
from abx_runes.yggdrasil.evidence_loader import load_evidence_bundles


def test_loader_sets_bridge_port_when_any_verified_bundle_present():
    """
    Evidence loader sets explicit_shadow_forecast_bridge port when at least one verified bundle is present.
    """
    with TemporaryDirectory() as td:
        p = Path(td) / "b.json"
        b = {
            "schema_version": SCHEMA_VERSION,
            "created_at": "2025-12-31T00:00:00+00:00",
            "bundle_hash": "",
            "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
            "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
            "calibration_refs": [],
        }
        p.write_text(json.dumps(lock_hash(b)), encoding="utf-8")

        res = load_evidence_bundles([str(p)])
        assert res.bundle_paths_ok == (str(p),)
        assert res.bundle_paths_bad == ()
        assert res.input_bundle.present.get("explicit_shadow_forecast_bridge") == "evidence_bundle"


def test_loader_rejects_invalid_bundle():
    """
    Evidence loader marks invalid bundles as bad.
    """
    with TemporaryDirectory() as td:
        p = Path(td) / "bad.json"
        p.write_text("not valid json", encoding="utf-8")

        res = load_evidence_bundles([str(p)])
        assert res.bundle_paths_ok == ()
        assert len(res.bundle_paths_bad) == 1
        assert res.bundle_paths_bad[0]["path"] == str(p)
        assert res.bundle_paths_bad[0]["reason"] == "invalid_json"
        # No port should be present
        assert "explicit_shadow_forecast_bridge" not in res.input_bundle.present


def test_loader_rejects_tampered_bundle():
    """
    Evidence loader detects hash mismatch (tampering).
    """
    with TemporaryDirectory() as td:
        p = Path(td) / "tampered.json"
        b = {
            "schema_version": SCHEMA_VERSION,
            "created_at": "2025-12-31T00:00:00+00:00",
            "bundle_hash": "",
            "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
            "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
            "calibration_refs": [],
        }
        b2 = lock_hash(b)
        # Tamper with the bundle after hashing
        b2["claims"][0]["statement"] = "tampered"
        p.write_text(json.dumps(b2), encoding="utf-8")

        res = load_evidence_bundles([str(p)])
        assert res.bundle_paths_ok == ()
        assert len(res.bundle_paths_bad) == 1
        assert res.bundle_paths_bad[0]["path"] == str(p)
        assert res.bundle_paths_bad[0]["reason"] == "hash_mismatch"
        # No port should be present
        assert "explicit_shadow_forecast_bridge" not in res.input_bundle.present


def test_loader_handles_missing_file():
    """
    Evidence loader marks missing files as bad.
    """
    res = load_evidence_bundles(["/nonexistent/path.json"])
    assert res.bundle_paths_ok == ()
    assert len(res.bundle_paths_bad) == 1
    assert res.bundle_paths_bad[0]["path"] == "/nonexistent/path.json"
    assert res.bundle_paths_bad[0]["reason"] == "missing"
    # No port should be present
    assert "explicit_shadow_forecast_bridge" not in res.input_bundle.present
