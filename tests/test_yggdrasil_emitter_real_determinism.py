from __future__ import annotations

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

        cfg = RealEmitterConfig(repo_root=root)
        m1 = emit_manifest_from_repo(cfg, _prov())
        m2 = emit_manifest_from_repo(cfg, _prov())

        assert m1["provenance"]["manifest_hash"] == m2["provenance"]["manifest_hash"]
        assert [n["id"] for n in m1["nodes"]] == [n["id"] for n in m2["nodes"]]
