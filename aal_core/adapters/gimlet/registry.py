"""
AAL-GIMLET Registry Module
Acronym registry enforcement and validation.
"""

import hashlib
import json
from typing import Optional, Dict, Any

from .contracts import AcronymDefinition, AcronymRegistry


# Canonical acronym definitions
_CANONICAL_DEFINITIONS = [
    AcronymDefinition(
        canonical_name="AAL-ABX",
        expansion="Abraxas eXecution framework",
        functional_definition="Four-phase ritual execution pattern (OPEN, ALIGN, CLEAR, SEAL)",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-SEED",
        expansion="Symbolic Entropy Elimination for Determinism",
        functional_definition="Deterministic entropy management and provenance tracking",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-ERS",
        expansion="Evidence-based Runtime Stabilization",
        functional_definition="Runtime tuning system with promotion governance and effect tracking",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-RUNE",
        expansion="Runtime Unit of Networked Execution",
        functional_definition="Executable unit with deterministic coupling and promotion states",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-YGGDRASIL",
        expansion="YGGDRASIL Graph Dependency Resolution And Scheduling Infrastructure Layer",
        functional_definition="Metadata-first topology layer for ABX-Runes execution planning",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-OSL",
        expansion="Overlay Service Layer",
        functional_definition="Integration layer for external services and overlay manifests",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-SCL",
        expansion="Self-Containment Layer",
        functional_definition="Capability gating and containment controls for alignment",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-SHADOW",
        expansion="Safe Heuristic Analysis and Detection Of Warnings",
        functional_definition="Observation-only monitoring lane for validation without execution",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-IOL",
        expansion="Input/Output Ledger",
        functional_definition="Append-only evidence ledger with deterministic serialization",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-VIZ",
        expansion="Visualization Intelligence Zone",
        functional_definition="Pattern-based visualization and scene rendering (Luma)",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-GIMLET",
        expansion="Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation",
        functional_definition="Deterministic ingress adapter for codebase analysis and integration",
        status="active"
    ),
    AcronymDefinition(
        canonical_name="AAL-IRIS",
        expansion="Intelligent Runtime Inspection System",
        functional_definition="Runtime introspection and diagnostic interface",
        status="active"
    ),
    # Aliases
    AcronymDefinition(
        canonical_name="ABX",
        expansion="Abraxas",
        functional_definition="Alias for AAL-ABX",
        status="alias",
        alias_for="AAL-ABX"
    ),
    AcronymDefinition(
        canonical_name="ERS",
        expansion="Evidence-based Runtime Stabilization",
        functional_definition="Alias for AAL-ERS",
        status="alias",
        alias_for="AAL-ERS"
    ),
]


def _compute_registry_hash(definitions: list[AcronymDefinition]) -> str:
    """Compute deterministic hash of registry"""
    # Sort by canonical name for determinism
    sorted_defs = sorted(definitions, key=lambda d: d.canonical_name)
    blob = json.dumps(
        [{"name": d.canonical_name, "expansion": d.expansion} for d in sorted_defs],
        sort_keys=True,
        separators=(",", ":")
    ).encode()
    return hashlib.sha256(blob).hexdigest()


def get_canonical_registry() -> AcronymRegistry:
    """Get the canonical AAL-core acronym registry"""
    registry_hash = _compute_registry_hash(_CANONICAL_DEFINITIONS)
    return AcronymRegistry(
        definitions=_CANONICAL_DEFINITIONS,
        registry_hash=registry_hash
    )


def validate_subsystem_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate subsystem name against canonical registry.

    Returns:
        (is_valid, warning_message)

    Enforcement:
        - Non-canonical names are INVALID
        - Deprecated names are VALID with warning
        - Aliases are VALID with warning
    """
    registry = get_canonical_registry()
    return registry.validate_name(name)


def enforce_registry_on_manifest(manifest: Dict[str, Any]) -> list[str]:
    """
    Enforce acronym registry on overlay manifest.

    Returns:
        List of validation errors
    """
    errors = []

    # Check overlay.id if present
    if "overlay" in manifest and "id" in manifest["overlay"]:
        overlay_id = manifest["overlay"]["id"]
        is_valid, warning = validate_subsystem_name(overlay_id)

        if not is_valid:
            errors.append(f"Non-canonical overlay ID: {overlay_id}")
        elif warning:
            errors.append(warning)

    # Check rune IDs for canonical prefixes
    if "runes" in manifest:
        for rune in manifest["runes"]:
            if "id" in rune:
                rune_id = rune["id"]
                # Rune IDs should start with canonical subsystem name
                parts = rune_id.split(".")
                if parts:
                    prefix = parts[0].upper()
                    # Check if it's a known subsystem prefix
                    is_valid, warning = validate_subsystem_name(prefix)
                    if not is_valid and not prefix.startswith("AAL-"):
                        errors.append(f"Rune ID '{rune_id}' uses non-canonical prefix: {prefix}")

    return errors


def get_definition(name: str) -> Optional[AcronymDefinition]:
    """Lookup acronym definition by name"""
    registry = get_canonical_registry()
    return registry.get_definition(name)


def list_all_definitions() -> list[AcronymDefinition]:
    """Get all canonical acronym definitions"""
    return _CANONICAL_DEFINITIONS.copy()
