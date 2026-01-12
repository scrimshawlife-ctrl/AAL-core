import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.pipeline.compile_scene import compile_scene
from aal_core.modules.luma.renderers.web_canvas import render_html_canvas


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


def _scene():
    frame = _fixed_frame(
        {
            "domain": "core",
            "motifs": ["alpha", "beta", "gamma"],
            "edges": [
                {
                    "source": "alpha",
                    "target": "beta",
                    "magnitude": 0.8,
                    "domain": "core",
                    "uncertainty": 0.15,
                },
                {
                    "source": "beta",
                    "target": "gamma",
                    "magnitude": 0.4,
                    "domain": "core",
                    "uncertainty": 0.35,
                },
            ],
            "field": {
                "grid_w": 2,
                "grid_h": 2,
                "values": [0.12, 0.58, 0.21, 0.9],
            },
            "field_uncertainty": {"uncertainty": [0.1, 0.2, 0.4, 0.0]},
        }
    )
    return compile_scene(frame, pattern_overrides=["motif_graph", "resonance_field"])


def test_web_canvas_is_deterministic():
    scene = _scene()
    hashes = [render_html_canvas(scene).content_sha256 for _ in range(6)]
    assert len(set(hashes)) == 1


def test_web_canvas_provenance_and_warning():
    scene = _scene()
    artifact = render_html_canvas(scene)
    warnings = getattr(artifact, "warnings", None)
    assert not warnings or "stub" not in str(warnings).lower()
    assert "luma-source-frame-provenance" in artifact.content
    assert scene.hash in artifact.content
