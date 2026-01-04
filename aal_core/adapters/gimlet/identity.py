"""
AAL-GIMLET Identity Module
Evidence-based classification of codebases.
"""

import json
from pathlib import Path
from typing import List, Optional

from .contracts import (
    Identity,
    IdentityKind,
    Evidence,
    FileMap,
    FileInfo,
)


def _check_aal_overlay_manifest(files: List[FileInfo]) -> Optional[Evidence]:
    """Check for .aal/overlays/*/manifest.json pattern"""
    for f in files:
        if f.path.startswith(".aal/overlays/") and f.path.endswith("/manifest.json"):
            return Evidence(
                file_path=f.path,
                rule_hit="AAL overlay manifest detected",
                confidence_contribution=0.9
            )
    return None


def _check_aal_core_imports(files: List[FileInfo]) -> List[Evidence]:
    """Check for aal_core imports in Python files (heuristic via path)"""
    # Note: This is a simplified heuristic. Full implementation would parse files.
    # For MVP, we check for presence of aal_core directory structure.
    evidence = []
    for f in files:
        if f.path.startswith("aal_core/") and f.language == "python":
            evidence.append(Evidence(
                file_path=f.path,
                rule_hit="aal_core package structure detected",
                confidence_contribution=0.15
            ))
            break  # Only count once
    return evidence


def _check_abx_runes_usage(files: List[FileInfo]) -> List[Evidence]:
    """Check for ABX-Runes registry or yggdrasil usage"""
    evidence = []
    for f in files:
        if "abx_runes" in f.path or "yggdrasil" in f.path:
            evidence.append(Evidence(
                file_path=f.path,
                rule_hit="ABX-Runes/Yggdrasil structure detected",
                confidence_contribution=0.2
            ))
            break
    return evidence


def _check_canon_structure(files: List[FileInfo]) -> List[Evidence]:
    """Check for canonical AAL folder structures"""
    evidence = []
    canon_patterns = [
        "aal_core/alignment/",
        "aal_core/governance/",
        "aal_core/ers/",
        "aal_core/ledger/",
        "aal_core/registry/",
        "aal_core/runes/",
        "alignment_core/",
    ]

    for pattern in canon_patterns:
        for f in files:
            if f.path.startswith(pattern):
                evidence.append(Evidence(
                    file_path=f.path,
                    rule_hit=f"Canon structure detected: {pattern}",
                    confidence_contribution=0.1
                ))
                break  # Only count each pattern once

    return evidence


def _check_aal_tests(files: List[FileInfo]) -> List[Evidence]:
    """Check for AAL-specific test patterns"""
    evidence = []
    test_patterns = [
        "test_promotion_scanner",
        "test_safe_set_key",
        "test_yggdrasil",
        "test_function_registry",
    ]

    for pattern in test_patterns:
        for f in files:
            if pattern in f.path:
                evidence.append(Evidence(
                    file_path=f.path,
                    rule_hit=f"AAL test pattern detected: {pattern}",
                    confidence_contribution=0.05
                ))
                break

    return evidence


def classify_identity(file_map: FileMap, source_path: str) -> Identity:
    """
    Classify codebase identity with evidence.

    Classification rules:
    1. AAL_OVERLAY: Has .aal/overlays/*/manifest.json
    2. AAL_SUBSYSTEM: Has aal_core structure + canon patterns (>= 0.3 confidence)
    3. EXTERNAL: Everything else

    Args:
        file_map: Normalized file map
        source_path: Original source path (for context)

    Returns:
        Identity with kind, confidence, and evidence
    """
    evidence: List[Evidence] = []

    # Rule 1: Check for overlay manifest (highest priority)
    overlay_evidence = _check_aal_overlay_manifest(file_map.files)
    if overlay_evidence:
        evidence.append(overlay_evidence)
        confidence = min(1.0, overlay_evidence.confidence_contribution)
        return Identity(
            kind=IdentityKind.AAL_OVERLAY,
            confidence=confidence,
            evidence=evidence
        )

    # Rule 2: Check for subsystem characteristics
    evidence.extend(_check_aal_core_imports(file_map.files))
    evidence.extend(_check_abx_runes_usage(file_map.files))
    evidence.extend(_check_canon_structure(file_map.files))
    evidence.extend(_check_aal_tests(file_map.files))

    # Compute total confidence (capped at 1.0)
    total_confidence = sum(e.confidence_contribution for e in evidence)
    total_confidence = min(1.0, total_confidence)

    # Classify based on confidence threshold
    if total_confidence >= 0.3:
        return Identity(
            kind=IdentityKind.AAL_SUBSYSTEM,
            confidence=total_confidence,
            evidence=evidence
        )
    else:
        # External code (may have some AAL-like patterns but not enough)
        return Identity(
            kind=IdentityKind.EXTERNAL,
            confidence=1.0 - total_confidence,  # Confidence in being external
            evidence=evidence if evidence else [
                Evidence(
                    file_path="<none>",
                    rule_hit="No AAL patterns detected",
                    confidence_contribution=1.0
                )
            ]
        )


def classify_with_manifest_validation(
    file_map: FileMap,
    source_path: str
) -> tuple[Identity, List[str]]:
    """
    Classify identity and validate overlay manifests if present.

    Returns:
        (Identity, validation_errors)
    """
    identity = classify_identity(file_map, source_path)
    validation_errors = []

    if identity.kind == IdentityKind.AAL_OVERLAY:
        # Validate manifest structure
        for f in file_map.files:
            if f.path.endswith("/manifest.json") and ".aal/overlays/" in f.path:
                # In production, would parse and validate against schema
                # For now, just check it exists and is valid JSON
                validation_errors.append(f"TODO: Validate manifest schema for {f.path}")

    return (identity, validation_errors)
