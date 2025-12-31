"""
AAL-core Function Registry: Validation Module
Validates FunctionDescriptor schema compliance and uniqueness.
"""

from typing import Any, Dict, List, Set


# Required fields per canonical FunctionDescriptor schema
REQUIRED_FIELDS: Set[str] = {
    "id",
    "name",
    "kind",
    "version",
    "owner",
    "entrypoint",
    "inputs_schema",
    "outputs_schema",
    "capabilities",
    "provenance",
}

# Optional fields
OPTIONAL_FIELDS: Set[str] = {
    "rune",
    "cost_hint",
}

# Valid kinds
VALID_KINDS: Set[str] = {
    "metric",
    "rune",
    "op",
    "overlay_op",
    "io",
}


def validate_descriptor(desc: Dict[str, Any]) -> None:
    """
    Validate a single FunctionDescriptor against canonical schema.

    Raises:
        ValueError: If descriptor is missing required fields or has invalid values
    """
    # Check required fields
    missing = REQUIRED_FIELDS - desc.keys()
    if missing:
        raise ValueError(
            f"FunctionDescriptor '{desc.get('id', 'unknown')}' missing required fields: {sorted(missing)}"
        )

    # Validate kind
    kind = desc.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(
            f"FunctionDescriptor '{desc['id']}' has invalid kind '{kind}'. Valid: {sorted(VALID_KINDS)}"
        )

    # Validate provenance structure
    prov = desc.get("provenance")
    if not isinstance(prov, dict):
        raise ValueError(
            f"FunctionDescriptor '{desc['id']}' provenance must be a dict"
        )

    required_prov_fields = {"repo", "commit", "artifact_hash", "generated_at"}
    missing_prov = required_prov_fields - prov.keys()
    if missing_prov:
        raise ValueError(
            f"FunctionDescriptor '{desc['id']}' provenance missing: {sorted(missing_prov)}"
        )

    # Validate schemas are dicts
    for schema_field in ["inputs_schema", "outputs_schema"]:
        if not isinstance(desc.get(schema_field), dict):
            raise ValueError(
                f"FunctionDescriptor '{desc['id']}' {schema_field} must be a dict (JSONSchema)"
            )

    # Validate capabilities is a list
    if not isinstance(desc.get("capabilities"), list):
        raise ValueError(
            f"FunctionDescriptor '{desc['id']}' capabilities must be a list"
        )


def validate_descriptors(descriptors: List[Dict[str, Any]]) -> None:
    """
    Validate a list of FunctionDescriptors for schema compliance and uniqueness.

    Raises:
        ValueError: If any descriptor is invalid or duplicate IDs exist
    """
    seen_ids: Set[str] = set()

    for desc in descriptors:
        # Validate individual descriptor
        validate_descriptor(desc)

        # Check for duplicate IDs
        desc_id = desc["id"]
        if desc_id in seen_ids:
            raise ValueError(
                f"Duplicate function id detected: '{desc_id}'"
            )
        seen_ids.add(desc_id)
