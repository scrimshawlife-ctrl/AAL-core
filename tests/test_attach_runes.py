"""
Tests for AAL-Core Rune Provenance Attachment
==============================================

Verifies that attach_runes:
- Does not mutate original payload
- Adds abx_runes metadata block
- Includes vendor provenance hashes
- Handles extras dict properly
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aal_core.runes.attach import attach_runes


def test_attach_runes_does_not_mutate_original():
    """Verify attach_runes creates a new dict and doesn't mutate the original."""
    original = {"data": "test", "value": 42}
    original_copy = original.copy()

    # This may fail if vendor doesn't exist, but we're testing mutation behavior
    try:
        result = attach_runes(original, used=["0001"], gate_state="OPEN")
        # Original should be unchanged
        assert original == original_copy, "Original payload was mutated"
        # Result should be different object
        assert result is not original, "Result is same object as original"
    except FileNotFoundError:
        # Vendor not present - test still passes for mutation check
        # Original wasn't mutated before the exception
        assert original == original_copy, "Original payload was mutated before exception"


def test_attach_runes_adds_metadata_block():
    """Verify abx_runes block is added with expected fields."""
    try:
        payload = {"action": "test"}
        result = attach_runes(payload, used=["0001", "0042"], gate_state="SEAL")

        # Check abx_runes block exists
        assert "abx_runes" in result, "Missing abx_runes block"

        # Check required fields
        abx = result["abx_runes"]
        assert abx["used"] == ["0001", "0042"], "Incorrect 'used' field"
        assert abx["gate_state"] == "SEAL", "Incorrect 'gate_state' field"
        assert "manifest_sha256" in abx, "Missing manifest_sha256"
        assert "vendor_lock_sha256" in abx, "Missing vendor_lock_sha256"

        # Verify hashes are hex strings
        assert isinstance(abx["manifest_sha256"], str), "manifest_sha256 not a string"
        assert isinstance(abx["vendor_lock_sha256"], str), "vendor_lock_sha256 not a string"
        assert len(abx["manifest_sha256"]) == 64, "manifest_sha256 not 64-char hex"
        assert len(abx["vendor_lock_sha256"]) == 64, "vendor_lock_sha256 not 64-char hex"

    except FileNotFoundError as e:
        pytest.skip(f"Vendor assets not present: {e}")


def test_attach_runes_includes_extras():
    """Verify extras dict is merged into abx_runes metadata."""
    try:
        payload = {"data": "test"}
        extras = {"custom_field": "custom_value", "count": 123}
        result = attach_runes(
            payload,
            used=["0001"],
            gate_state="CLEAR",
            extras=extras
        )

        abx = result["abx_runes"]
        assert abx["custom_field"] == "custom_value", "Missing extra field"
        assert abx["count"] == 123, "Missing extra count field"

    except FileNotFoundError as e:
        pytest.skip(f"Vendor assets not present: {e}")


def test_attach_runes_preserves_payload_data():
    """Verify original payload data is preserved in result."""
    try:
        payload = {"key1": "value1", "key2": [1, 2, 3], "nested": {"a": "b"}}
        result = attach_runes(payload, used=[], gate_state="OPEN")

        # All original keys should be present
        assert result["key1"] == "value1"
        assert result["key2"] == [1, 2, 3]
        assert result["nested"] == {"a": "b"}

    except FileNotFoundError as e:
        pytest.skip(f"Vendor assets not present: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
