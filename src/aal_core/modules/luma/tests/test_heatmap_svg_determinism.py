import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.pipeline.compile_scene import compile_scene
from aal_core.modules.luma.renderers.svg_static import render_svg


def _fixed_frame(payload: dict) -> dict:
    return {
        "utc": "2026-01-02T00:00:00Z",
        "module": "test.luma",
        "payload": payload,
        "abx_runes": {"used": [], "gate_state": "CLEAR"},
        "provenance": {
            "vendor_lock_sha256": "0" * 64,
            "manifest_sha256": "1" * 64,
        },
    }


def test_heatmap_svg_is_stable():
    frame = _fixed_frame(
        {
            "domains": ["alpha", "beta"],
            "motifs": [
                {"id": "m1", "domain_id": "alpha", "salience": 0.9},
                {"id": "m2", "domain_id": "beta", "salience": 0.4},
                {"id": "m3", "domain_id": "alpha", "salience": 0.2},
            ],
        }
    )
    scene = compile_scene(frame, pattern_overrides=["motif_domain_heatmap"])

    hashes = [render_svg(scene).content_sha256 for _ in range(12)]
    assert len(set(hashes)) == 1
