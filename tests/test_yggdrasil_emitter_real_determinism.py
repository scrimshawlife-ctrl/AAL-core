from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from abx_runes.yggdrasil.emitter_real import RealEmitterConfig, emit_manifest_from_repo
from abx_runes.yggdrasil.schema import ProvenanceSpec


def _prov():
    return ProvenanceSpec(
        schema_version="yggdrasil-ir/0.1",
        manifest_hash="",
        created_at="2025-12-30T00:00:00+00:00",
        updated_at="2025-12-30T00:00:00+00:00",
        source_commit="test",
    )


def test_emitter_is_deterministic_for_same_filesystem():
    with TemporaryDirectory() as td:
        root = Path(td)
        overlays = root / ".aal" / "overlays"
        (overlays / "abraxas").mkdir(parents=True)
        (overlays / "psyfi").mkdir(parents=True)
        (overlays / "beatoven").mkdir(parents=True)

        # declare a rune inside abraxas overlay that depends on realm.asgard (cross-realm) to force link generation
        (overlays / "abraxas" / "manifest.json").write_text(
            json.dumps({"runes": [{"id": "abraxas.r1", "depends_on": ["realm.asgard"]}]}),
            encoding="utf-8"
        )

        cfg = RealEmitterConfig(repo_root=root)
        m1 = emit_manifest_from_repo(cfg, _prov())
        m2 = emit_manifest_from_repo(cfg, _prov())

        assert m1["provenance"]["manifest_hash"] == m2["provenance"]["manifest_hash"]
        assert [n["id"] for n in m1["nodes"]] == [n["id"] for n in m2["nodes"]]

        # link should exist for cross-realm edge
        edges = {(l["from_node"], l["to_node"]) for l in m1.get("links", [])}
        assert ("realm.asgard", "abraxas.r1") in edges


def test_emitter_detects_forbidden_shadow_to_forecast_crossing():
    """
    Verify that shadow->forecast crossings are flagged as forbidden
    and do not get auto-allowed in the generated link.
    """
    with TemporaryDirectory() as td:
        root = Path(td)
        overlays = root / ".aal" / "overlays"
        (overlays / "shadow_overlay").mkdir(parents=True)

        # Declare a shadow rune that tries to feed a forecast rune (cross-realm)
        # shadow_overlay is in HEL/shadow by default, but we'll use classify to make it explicit
        classify = {
            "overlay.shadow_overlay": {"realm": "HEL", "lane": "shadow"},
            "shadow_overlay.shadow_rune": {"realm": "HEL", "lane": "shadow"},
            "shadow_overlay.forecast_rune": {"realm": "ASGARD", "lane": "forecast"},
        }
        (root / "yggdrasil.classify.json").write_text(json.dumps(classify), encoding="utf-8")

        # Shadow rune -> forecast rune dependency (forbidden bridge)
        (overlays / "shadow_overlay" / "manifest.json").write_text(
            json.dumps({
                "runes": [
                    {"id": "shadow_overlay.shadow_rune", "depends_on": []},
                    {"id": "shadow_overlay.forecast_rune", "depends_on": ["shadow_overlay.shadow_rune"]},
                ]
            }),
            encoding="utf-8"
        )

        cfg = RealEmitterConfig(repo_root=root)
        m = emit_manifest_from_repo(cfg, _prov())

        # Should have forbidden crossings in lint report
        forbidden = m["provenance"]["lint"]["forbidden_crossings"]
        assert len(forbidden) > 0
        assert any(
            f["from"] == "shadow_overlay.shadow_rune" and f["to"] == "shadow_overlay.forecast_rune"
            for f in forbidden
        )

        # Link should exist but with NO allowed_lanes (stub link)
        links = {(l["from_node"], l["to_node"]): l for l in m.get("links", [])}
        link = links.get(("shadow_overlay.shadow_rune", "shadow_overlay.forecast_rune"))
        assert link is not None
        assert link["allowed_lanes"] == []  # Not auto-allowed
        assert "EXPLICIT_SHADOW_FORECAST_BRIDGE" in link["evidence_required"]
