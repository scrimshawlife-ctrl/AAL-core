import sys
from pathlib import Path

# Add src to path for imports (repo convention)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aal_core.modules.luma import render


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


def test_luma_render_smoke_static_svg():
    artifacts = render(_fixed_frame({"motifs": ["m1", "m2"]}), mode="static")
    assert len(artifacts) == 1
    a = artifacts[0]
    assert a.mime_type == "image/svg+xml"
    assert a.scene_hash
    assert a.content and "<svg" in a.content
