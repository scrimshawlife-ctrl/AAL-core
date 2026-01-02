import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.scene_ir import LumaSceneIR
from aal_core.modules.luma.pipeline.compile_scene import compile_scene


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


def test_scene_hash_matches_recomputed_hash():
    scene = compile_scene(_fixed_frame({"motifs": ["x"]}))
    assert LumaSceneIR.compute_hash(scene) == scene.hash


def test_missing_input_is_explicit_not_computable():
    scene = compile_scene(_fixed_frame({}))
    assert scene.entities == "not_computable"
    assert scene.edges == "not_computable"
