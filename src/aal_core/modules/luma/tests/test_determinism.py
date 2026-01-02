import sys
from pathlib import Path

# Ensure `src/` is importable (repo uses split package layout)
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

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


def test_scene_hash_is_deterministic_for_same_input():
    frame = _fixed_frame(
        {
            "motifs": ["alpha", "beta"],
            "edges": [{"source": "alpha", "target": "beta", "magnitude": 4.0}],
        }
    )
    s1 = compile_scene(frame)
    s2 = compile_scene(frame)
    assert s1.hash == s2.hash


def test_12_run_invariance():
    frame = _fixed_frame({"motifs": ["a", "b", "c"]})
    hashes = {compile_scene(frame).hash for _ in range(12)}
    assert len(hashes) == 1
