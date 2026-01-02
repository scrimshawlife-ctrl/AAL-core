import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

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


def test_temporal_braid_svg_is_stable():
    frame = _fixed_frame(
        {
            "motifs": ["a", "b"],
            "timeline": [
                {"t": "2025-12-01T00:00:00Z", "motifs": ["a"]},
                {"t": "2025-12-02T00:00:00Z", "motifs": ["a", "b"]},
                {"t": "2025-12-03T00:00:00Z", "motifs": ["b"]},
            ],
        }
    )

    a1 = render(frame, mode="static")[0]
    a2 = render(frame, mode="static")[0]
    assert a1.content_sha256 == a2.content_sha256

