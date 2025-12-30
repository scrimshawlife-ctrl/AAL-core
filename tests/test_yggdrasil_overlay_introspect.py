from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from abx_runes.yggdrasil.overlay_introspect import load_overlay_manifest_json, extract_declared_runes


def test_extract_declared_runes_is_deterministic():
    m = {
        "runes": [
            {"id": "b.rune", "depends_on": ["x"]},
            {"id": "a.rune", "depends_on": ["y"]},
        ]
    }
    runes = extract_declared_runes(m)
    assert [r.rune_id for r in runes] == ["a.rune", "b.rune"]


def test_load_overlay_manifest_json_reads_manifest_json():
    with TemporaryDirectory() as td:
        d = Path(td)
        (d / "manifest.json").write_text(json.dumps({"runes": [{"id": "a"}]}), encoding="utf-8")
        loaded = load_overlay_manifest_json(d)
        assert loaded is not None
        assert loaded.get("runes")[0]["id"] == "a"
