from __future__ import annotations

import pytest

from abx_runes.yggdrasil.overlay_schema_validate import (
    validate_overlay_manifest,
    OverlaySchemaError,
)


def test_valid_minimal_overlay_manifest():
    """Minimal valid manifest with only required fields."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
    }
    # Should not raise
    validate_overlay_manifest(manifest)


def test_valid_overlay_manifest_with_runes():
    """Valid manifest with runes declared."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {
            "id": "abraxas",
            "description": "Test overlay",
            "default_realm": "MIDGARD",
            "default_lane": "neutral",
        },
        "runes": [
            {
                "id": "abraxas.rune1",
                "depends_on": ["kernel.registry"],
                "realm": "HEL",
                "lane": "shadow",
                "promotion_state": "candidate",
                "tags": ["test"],
            }
        ],
    }
    # Should not raise
    validate_overlay_manifest(manifest)


def test_valid_overlay_manifest_with_typed_ports():
    """Valid manifest with typed inputs/outputs."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [
            {
                "id": "test.rune",
                "inputs": [
                    {"name": "data", "dtype": "pd.DataFrame", "required": True}
                ],
                "outputs": [{"name": "result", "dtype": "str"}],
            }
        ],
    }
    # Should not raise
    validate_overlay_manifest(manifest)


def test_rejects_missing_schema_version():
    """Schema version is required."""
    manifest = {"overlay": {"id": "test"}}
    with pytest.raises(OverlaySchemaError, match="schema_version"):
        validate_overlay_manifest(manifest)


def test_rejects_wrong_schema_version():
    """Schema version must be exactly 'yggdrasil-overlay/0.1'."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.2",
        "overlay": {"id": "test"},
    }
    with pytest.raises(OverlaySchemaError, match="schema_version"):
        validate_overlay_manifest(manifest)


def test_rejects_missing_overlay_id():
    """overlay.id is required."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {},
    }
    with pytest.raises(OverlaySchemaError, match="overlay.id"):
        validate_overlay_manifest(manifest)


def test_rejects_empty_overlay_id():
    """overlay.id must be non-empty."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": ""},
    }
    with pytest.raises(OverlaySchemaError, match="overlay.id"):
        validate_overlay_manifest(manifest)


def test_rejects_invalid_default_realm():
    """default_realm must be valid."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test", "default_realm": "INVALID"},
    }
    with pytest.raises(OverlaySchemaError, match="default_realm"):
        validate_overlay_manifest(manifest)


def test_rejects_invalid_default_lane():
    """default_lane must be valid."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test", "default_lane": "invalid"},
    }
    with pytest.raises(OverlaySchemaError, match="default_lane"):
        validate_overlay_manifest(manifest)


def test_rejects_duplicate_rune_ids():
    """Rune IDs must be unique within overlay."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [
            {"id": "test.rune"},
            {"id": "test.rune"},  # Duplicate
        ],
    }
    with pytest.raises(OverlaySchemaError, match="Duplicate rune id"):
        validate_overlay_manifest(manifest)


def test_rejects_invalid_rune_realm():
    """Rune realm must be valid."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [{"id": "test.rune", "realm": "INVALID"}],
    }
    with pytest.raises(OverlaySchemaError, match="realm invalid"):
        validate_overlay_manifest(manifest)


def test_rejects_invalid_rune_lane():
    """Rune lane must be valid."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [{"id": "test.rune", "lane": "invalid"}],
    }
    with pytest.raises(OverlaySchemaError, match="lane invalid"):
        validate_overlay_manifest(manifest)


def test_rejects_invalid_promotion_state():
    """Promotion state must be valid."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [{"id": "test.rune", "promotion_state": "invalid"}],
    }
    with pytest.raises(OverlaySchemaError, match="promotion_state invalid"):
        validate_overlay_manifest(manifest)


def test_rejects_port_missing_name():
    """Port name is required."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [{"id": "test.rune", "inputs": [{"dtype": "str"}]}],
    }
    with pytest.raises(OverlaySchemaError, match="name required"):
        validate_overlay_manifest(manifest)


def test_rejects_port_missing_dtype():
    """Port dtype is required."""
    manifest = {
        "schema_version": "yggdrasil-overlay/0.1",
        "overlay": {"id": "test"},
        "runes": [{"id": "test.rune", "outputs": [{"name": "result"}]}],
    }
    with pytest.raises(OverlaySchemaError, match="dtype required"):
        validate_overlay_manifest(manifest)
