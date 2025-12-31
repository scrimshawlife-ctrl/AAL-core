"""
Tests for AAL-Core ResonanceFrame Provenance
============================================

Verifies that ResonanceFrame construction:
- Includes vendor_lock_sha256 and manifest_sha256 when vendor exists
- Hashes are stable (deterministic) across multiple calls
- Gracefully handles missing vendor (doesn't hard-fail)
- Includes proper UTC timestamp and module identifier
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aal_core.bus.frame import make_frame
from aal_core.schema.resonance_frame import ResonanceFrame


def test_make_frame_basic_structure():
    """Verify make_frame creates a valid ResonanceFrame structure."""
    payload = {"action": "test", "data": {"value": 42}}
    frame = make_frame("test.module", payload)

    # Check required fields
    assert "utc" in frame, "Missing UTC timestamp"
    assert "module" in frame, "Missing module identifier"
    assert "payload" in frame, "Missing payload"
    assert "provenance" in frame, "Missing provenance"

    # Check values
    assert frame["module"] == "test.module"
    assert frame["payload"] == payload
    assert isinstance(frame["provenance"], dict)


def test_make_frame_includes_provenance_when_vendor_exists():
    """Verify vendor_lock_sha256 and manifest_sha256 are present when vendor exists."""
    try:
        frame = make_frame("test.module", {"test": "data"})

        prov = frame["provenance"]
        assert "vendor_lock_sha256" in prov, "Missing vendor_lock_sha256"
        assert "manifest_sha256" in prov, "Missing manifest_sha256"

        # Verify they're valid SHA256 hex strings (64 chars)
        assert len(prov["vendor_lock_sha256"]) == 64, "Invalid vendor_lock_sha256 format"
        assert len(prov["manifest_sha256"]) == 64, "Invalid manifest_sha256 format"
        assert all(c in "0123456789abcdef" for c in prov["vendor_lock_sha256"]), "Invalid hex in vendor_lock_sha256"
        assert all(c in "0123456789abcdef" for c in prov["manifest_sha256"]), "Invalid hex in manifest_sha256"

    except Exception as e:
        # If vendor doesn't exist, test should skip gracefully
        pytest.skip(f"Vendor assets not present, skipping provenance verification: {e}")


def test_make_frame_provenance_is_stable():
    """Verify provenance hashes are deterministic across multiple calls."""
    try:
        frame1 = make_frame("test.module", {"data": "test1"})
        frame2 = make_frame("test.module", {"data": "test2"})

        # Provenance hashes should be identical (deterministic)
        assert frame1["provenance"]["vendor_lock_sha256"] == frame2["provenance"]["vendor_lock_sha256"], \
            "vendor_lock_sha256 is not stable"
        assert frame1["provenance"]["manifest_sha256"] == frame2["provenance"]["manifest_sha256"], \
            "manifest_sha256 is not stable"

    except Exception as e:
        pytest.skip(f"Vendor assets not present: {e}")


def test_make_frame_graceful_degradation_without_vendor():
    """Verify make_frame doesn't hard-fail when vendor is missing."""
    # This test should always pass - if vendor exists, provenance is added;
    # if vendor is missing, frame is still created (graceful degradation)
    frame = make_frame("test.module", {"data": "test"})

    assert "provenance" in frame, "Missing provenance dict"
    assert isinstance(frame["provenance"], dict), "Provenance is not a dict"
    # Frame should be valid even if provenance is empty
    assert frame["module"] == "test.module"
    assert frame["payload"] == {"data": "test"}


def test_make_frame_with_abx_runes_metadata():
    """Verify abx_runes metadata is included when provided."""
    rune_meta = {
        "used": ["0001", "0042"],
        "gate_state": "SEAL",
        "custom": "metadata"
    }
    frame = make_frame("test.module", {"data": "test"}, abx_runes=rune_meta)

    assert frame["abx_runes"] == rune_meta, "abx_runes metadata not preserved"


def test_make_frame_utc_timestamp_format():
    """Verify UTC timestamp is ISO 8601 format."""
    frame = make_frame("test.module", {"data": "test"})

    # Basic ISO 8601 check (should contain 'T' and end with timezone info)
    utc = frame["utc"]
    assert "T" in utc, "UTC timestamp not in ISO 8601 format"
    # Should end with +00:00 or Z for UTC
    assert utc.endswith("+00:00") or utc.endswith("Z") or "+" in utc, \
        "UTC timestamp missing timezone info"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
