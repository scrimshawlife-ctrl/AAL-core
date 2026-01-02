import sys
from pathlib import Path

# Ensure `src/` is importable (repo uses split package layout)
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma import render
from aal_core.modules.luma.pipeline.compile_scene import compile_scene


def _fixed_frame(payload: dict) -> dict:
    return {
        "utc": "2026-01-02T00:00:00Z",
        "module": "test.luma",
        "payload": payload,
        "abx_runes": {"used": ["0001"], "gate_state": "CLEAR"},
        "provenance": {
            "vendor_lock_sha256": "0" * 64,
            "manifest_sha256": "1" * 64,
        },
    }


def _assert_12_run_invariance(fn):
    vals = [fn() for _ in range(12)]
    assert len(set(vals)) == 1


def test_12_run_scene_hash_invariance_plate():
    frame = _fixed_frame(
        {
            "motifs": ["policy", "compute", "vol"],
            "edges": [{"source": "policy", "target": "compute", "magnitude": 4.0}],
            "domains": [
                {"domain": "Geopolitics", "subdomains": ["Elections"]},
                {"domain": "Tech/AI", "subdomains": ["LLMs"]},
                {"domain": "Finance", "subdomains": ["Markets"]},
            ],
            "flows": [
                {"source_domain": "Tech/AI", "target_domain": "Finance", "value": 0.8},
                {"source_domain": "Geopolitics", "target_domain": "Tech/AI", "value": 0.3},
                {"source_domain": "Geopolitics", "target_domain": "Finance", "value": 0.5},
            ],
            "timeline": [
                {"t": "2025-12-20T12:00:00Z", "motifs": ["policy"]},
                {"t": "2025-12-22T12:00:00Z", "motifs": ["compute"]},
                {"t": "2025-12-24T12:00:00Z", "motifs": ["vol", "policy"]},
            ],
        }
    )

    _assert_12_run_invariance(lambda: compile_scene(frame).hash)


def test_12_run_svg_hash_invariance_plate():
    frame = _fixed_frame(
        {
            "motifs": ["policy", "compute", "vol"],
            "edges": [{"source": "policy", "target": "compute", "magnitude": 9.0}],
            "domains": ["Geopolitics", "Tech/AI", "Finance"],
            "flows": [
                {"source_domain": "Tech/AI", "target_domain": "Finance", "value": 0.8, "uncertainty": 0.2},
                {"source_domain": "Geopolitics", "target_domain": "Tech/AI", "value": 0.3, "uncertainty": 0.4},
            ],
            "timeline": [
                {"t": "2025-12-01T00:00:00Z", "motifs": ["policy"]},
                {"t": "2025-12-02T00:00:00Z", "motifs": ["policy", "compute"]},
                {"t": "2025-12-03T00:00:00Z", "motifs": ["vol"]},
            ],
        }
    )

    _assert_12_run_invariance(lambda: render(frame, mode="static")[0].content_sha256)

