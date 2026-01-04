"""
AAL-GIMLET Registry Tests
Test acronym registry enforcement and validation.
"""

import pytest

from aal_core.adapters.gimlet.registry import (
    get_canonical_registry,
    validate_subsystem_name,
    enforce_registry_on_manifest,
    get_definition,
    list_all_definitions,
)


def test_get_canonical_registry():
    """Canonical registry contains expected subsystems"""
    registry = get_canonical_registry()

    assert len(registry.definitions) > 0, "Registry should not be empty"
    assert registry.registry_hash, "Registry should have deterministic hash"

    # Check for key subsystems
    names = [d.canonical_name for d in registry.definitions]
    assert "AAL-GIMLET" in names
    assert "AAL-ERS" in names
    assert "AAL-SEED" in names
    assert "AAL-RUNE" in names


def test_validate_canonical_name():
    """Canonical subsystem names validate successfully"""
    is_valid, warning = validate_subsystem_name("AAL-GIMLET")
    assert is_valid is True
    assert warning is None

    is_valid, warning = validate_subsystem_name("AAL-ERS")
    assert is_valid is True
    assert warning is None


def test_validate_non_canonical_name():
    """Non-canonical names are rejected"""
    is_valid, warning = validate_subsystem_name("CUSTOM-SUBSYSTEM")
    assert is_valid is False
    assert "Non-canonical" in warning


def test_validate_alias_name():
    """Alias names are valid but warn"""
    # ABX is an alias for AAL-ABX
    is_valid, warning = validate_subsystem_name("ABX")
    assert is_valid is True
    assert warning is not None
    assert "alias" in warning.lower()


def test_get_definition():
    """Get definition by name"""
    defn = get_definition("AAL-GIMLET")
    assert defn is not None
    assert defn.canonical_name == "AAL-GIMLET"
    assert "Gateway" in defn.expansion
    assert defn.status == "active"

    # Non-existent
    defn = get_definition("NONEXISTENT")
    assert defn is None


def test_list_all_definitions():
    """List all definitions"""
    definitions = list_all_definitions()
    assert len(definitions) > 0

    # Should include both active and aliases
    names = [d.canonical_name for d in definitions]
    assert "AAL-GIMLET" in names
    assert "ABX" in names  # Alias


def test_registry_deterministic_hash():
    """Registry hash is deterministic"""
    registry1 = get_canonical_registry()
    registry2 = get_canonical_registry()

    assert registry1.registry_hash == registry2.registry_hash


def test_enforce_registry_on_manifest_valid():
    """Valid manifest passes enforcement"""
    manifest = {
        "overlay": {
            "id": "AAL-GIMLET"
        },
        "runes": [
            {"id": "aal-gimlet.inspect.v1"}
        ]
    }

    errors = enforce_registry_on_manifest(manifest)
    # Should have no errors (or only warnings about lowercase prefix)
    critical_errors = [e for e in errors if "Non-canonical overlay ID" in e]
    assert len(critical_errors) == 0


def test_enforce_registry_on_manifest_invalid_overlay():
    """Invalid overlay ID is flagged"""
    manifest = {
        "overlay": {
            "id": "custom-overlay"
        }
    }

    errors = enforce_registry_on_manifest(manifest)
    assert len(errors) > 0
    assert any("Non-canonical overlay ID" in e for e in errors)


def test_enforce_registry_on_manifest_non_canonical_rune():
    """Non-canonical rune prefix is flagged"""
    manifest = {
        "runes": [
            {"id": "UNKNOWN.rune.v1"}
        ]
    }

    errors = enforce_registry_on_manifest(manifest)
    # Should flag non-canonical prefix
    assert len(errors) > 0


def test_acronym_definition_immutability():
    """AcronymDefinition is immutable (frozen dataclass)"""
    defn = get_definition("AAL-GIMLET")

    with pytest.raises(Exception):  # FrozenInstanceError
        defn.canonical_name = "CHANGED"


def test_registry_immutability():
    """AcronymRegistry is immutable"""
    registry = get_canonical_registry()

    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        registry.registry_hash = "changed"


def test_all_active_subsystems_have_expansions():
    """All active subsystems have non-empty expansions"""
    definitions = list_all_definitions()

    for defn in definitions:
        if defn.status == "active":
            assert defn.expansion, f"{defn.canonical_name} missing expansion"
            assert defn.functional_definition, \
                f"{defn.canonical_name} missing functional definition"


def test_all_aliases_reference_valid_subsystems():
    """All aliases point to valid canonical names"""
    registry = get_canonical_registry()
    definitions = list_all_definitions()

    canonical_names = {d.canonical_name for d in definitions if d.status == "active"}

    for defn in definitions:
        if defn.status == "alias":
            assert defn.alias_for is not None, \
                f"Alias {defn.canonical_name} missing alias_for"
            assert defn.alias_for in canonical_names, \
                f"Alias {defn.canonical_name} references unknown {defn.alias_for}"


def test_no_duplicate_canonical_names():
    """No duplicate canonical names in registry"""
    definitions = list_all_definitions()
    names = [d.canonical_name for d in definitions]

    assert len(names) == len(set(names)), \
        f"Duplicate names found: {[n for n in names if names.count(n) > 1]}"


def test_registry_get_definition_case_sensitive():
    """Registry lookup is case-sensitive"""
    # Exact match
    assert get_definition("AAL-GIMLET") is not None

    # Wrong case
    assert get_definition("aal-gimlet") is None
    assert get_definition("AAL-gimlet") is None


def test_validate_name_returns_tuple():
    """validate_subsystem_name always returns (bool, Optional[str])"""
    result = validate_subsystem_name("AAL-GIMLET")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert result[1] is None or isinstance(result[1], str)


def test_gimlet_definition_matches_docs():
    """GIMLET definition matches canonical specification"""
    defn = get_definition("AAL-GIMLET")

    assert defn is not None
    assert defn.canonical_name == "AAL-GIMLET"
    assert "Gateway" in defn.expansion
    assert "Integration" in defn.expansion
    assert "Modularization" in defn.expansion
    assert "Legibility" in defn.expansion
    assert "Evaluation" in defn.expansion
    assert "Transformation" in defn.expansion
    assert defn.status == "active"
    assert "ingress adapter" in defn.functional_definition.lower()


def test_enforcement_empty_manifest():
    """Empty manifest produces no errors"""
    errors = enforce_registry_on_manifest({})
    assert len(errors) == 0


def test_enforcement_manifest_without_overlay():
    """Manifest without overlay section is valid"""
    manifest = {
        "runes": []
    }
    errors = enforce_registry_on_manifest(manifest)
    # No overlay ID to validate, should pass
    assert len([e for e in errors if "overlay" in e.lower()]) == 0
