"""
AAL-GIMLET Scoring Module
Deterministic codebase scoring (0-100).
"""

from typing import List

from .contracts import (
    FileMap,
    Identity,
    IdentityKind,
    IntegrationPatchPlan,
    OptimizationRoadmap,
    GimletScore,
    ScoreComponent,
)


def _score_integratability(
    file_map: FileMap,
    identity: Identity,
    integration_plan: IntegrationPatchPlan | None
) -> ScoreComponent:
    """
    Score integratability (0-30 points).

    Factors:
    - AAL_OVERLAY: Base 25 points, -5 per critical error
    - AAL_SUBSYSTEM: Base 20 points, -5 per critical error
    - EXTERNAL: Base 5 points (needs roadmap)
    - Test coverage: +5 points
    """
    evidence = []
    max_score = 30.0

    if identity.kind == IdentityKind.AAL_OVERLAY:
        score = 25.0
        evidence.append("AAL overlay detected (+25)")
    elif identity.kind == IdentityKind.AAL_SUBSYSTEM:
        score = 20.0
        evidence.append("AAL subsystem detected (+20)")
    else:
        score = 5.0
        evidence.append("External code, requires roadmap (+5)")

    # Deduct for integration errors
    if integration_plan:
        error_count = sum(1 for i in integration_plan.issues if i.severity == "error")
        deduction = min(score, error_count * 5.0)
        if deduction > 0:
            score -= deduction
            evidence.append(f"Integration errors: -{deduction} ({error_count} errors)")

    # Bonus for tests
    has_tests = any("test_" in f.path or f.path.startswith("tests/") for f in file_map.files)
    if has_tests:
        score = min(max_score, score + 5.0)
        evidence.append("Test coverage detected (+5)")
    else:
        evidence.append("No tests detected (0)")

    return ScoreComponent(
        name="Integratability",
        score=score,
        max_score=max_score,
        evidence=evidence
    )


def _score_rune_fit(
    file_map: FileMap,
    identity: Identity,
    optimization_roadmap: OptimizationRoadmap | None
) -> ScoreComponent:
    """
    Score ABX-Rune fit (0-30 points).

    Factors:
    - Existing rune usage: +15 points
    - Modular structure: +10 points
    - Clear API boundaries: +5 points
    """
    evidence = []
    max_score = 30.0
    score = 0.0

    # Check for existing rune usage
    has_runes = any("rune" in f.path.lower() or "abx" in f.path.lower() for f in file_map.files)
    if has_runes:
        score += 15.0
        evidence.append("Existing ABX-Runes usage (+15)")
    else:
        evidence.append("No existing rune usage (0)")

    # Check for modular structure (presence of __init__.py, package organization)
    python_packages = sum(1 for f in file_map.files if f.path.endswith("__init__.py"))
    if python_packages >= 3:
        score += 10.0
        evidence.append(f"Modular structure: {python_packages} packages (+10)")
    elif python_packages > 0:
        score += 5.0
        evidence.append(f"Some modularity: {python_packages} packages (+5)")
    else:
        evidence.append("No package structure (0)")

    # Check for API boundaries (presence of api/, routes/, endpoints/)
    api_indicators = ["api/", "routes/", "endpoints/", "handlers/", "interface/"]
    has_api = any(
        any(indicator in f.path.lower() for indicator in api_indicators)
        for f in file_map.files
    )
    if has_api:
        score += 5.0
        evidence.append("Clear API boundaries (+5)")
    else:
        evidence.append("No explicit API layer (0)")

    return ScoreComponent(
        name="Rune-Fit",
        score=score,
        max_score=max_score,
        evidence=evidence
    )


def _score_determinism_readiness(file_map: FileMap) -> ScoreComponent:
    """
    Score determinism readiness (0-20 points).

    Factors:
    - Provenance patterns: +5 points
    - Test presence: +5 points
    - No obvious entropy sources: +5 points
    - Structured config: +5 points
    """
    evidence = []
    max_score = 20.0
    score = 0.0

    # Check for provenance patterns
    provenance_indicators = ["provenance", "ledger", "evidence", "audit"]
    has_provenance = any(
        any(indicator in f.path.lower() for indicator in provenance_indicators)
        for f in file_map.files
    )
    if has_provenance:
        score += 5.0
        evidence.append("Provenance patterns detected (+5)")
    else:
        evidence.append("No provenance tracking (0)")

    # Test presence
    test_count = sum(1 for f in file_map.files if "test_" in f.path or f.path.startswith("tests/"))
    if test_count >= 5:
        score += 5.0
        evidence.append(f"Strong test coverage: {test_count} test files (+5)")
    elif test_count > 0:
        score += 2.5
        evidence.append(f"Some tests: {test_count} test files (+2.5)")
    else:
        evidence.append("No tests (0)")

    # Check for entropy sources (random, uuid, time without SEED)
    # This is a heuristic - would need code analysis for accuracy
    has_seed = any("seed" in f.path.lower() for f in file_map.files)
    if has_seed:
        score += 5.0
        evidence.append("SEED pattern detected (+5)")
    else:
        score += 2.5
        evidence.append("No explicit SEED, assuming manageable entropy (+2.5)")

    # Structured config
    config_files = [
        f for f in file_map.files
        if f.path.endswith((".toml", ".yaml", ".yml", ".json"))
        and any(c in f.path.lower() for c in ["config", "settings", "manifest"])
    ]
    if config_files:
        score += 5.0
        evidence.append(f"Structured config: {len(config_files)} file(s) (+5)")
    else:
        evidence.append("No config files (0)")

    return ScoreComponent(
        name="Determinism Readiness",
        score=score,
        max_score=max_score,
        evidence=evidence
    )


def _score_rent_potential(file_map: FileMap, identity: Identity) -> ScoreComponent:
    """
    Score complexity rent potential (0-20 points).

    Factors:
    - Large codebase (>10k LOC equiv): +10 points
    - Multiple languages: +5 points
    - Clear subsystem boundaries: +5 points
    """
    evidence = []
    max_score = 20.0
    score = 0.0

    # Estimate LOC from file count and size
    # Heuristic: 50 bytes per LOC average
    estimated_loc = file_map.total_size_bytes / 50
    if estimated_loc > 10000:
        score += 10.0
        evidence.append(f"Large codebase: ~{int(estimated_loc):,} LOC (+10)")
    elif estimated_loc > 1000:
        score += 5.0
        evidence.append(f"Medium codebase: ~{int(estimated_loc):,} LOC (+5)")
    else:
        evidence.append(f"Small codebase: ~{int(estimated_loc):,} LOC (0)")

    # Multiple languages
    lang_count = len(file_map.languages)
    if lang_count >= 3:
        score += 5.0
        evidence.append(f"Polyglot: {lang_count} languages (+5)")
    elif lang_count == 2:
        score += 2.5
        evidence.append(f"Two languages (+2.5)")
    else:
        evidence.append(f"Single language (0)")

    # Subsystem boundaries (heuristic: top-level directories)
    top_level_dirs = set()
    for f in file_map.files:
        parts = f.path.split("/")
        if len(parts) > 1 and not parts[0].startswith("."):
            top_level_dirs.add(parts[0])

    if len(top_level_dirs) >= 5:
        score += 5.0
        evidence.append(f"Clear boundaries: {len(top_level_dirs)} top-level modules (+5)")
    elif len(top_level_dirs) >= 2:
        score += 2.5
        evidence.append(f"Some boundaries: {len(top_level_dirs)} modules (+2.5)")
    else:
        evidence.append("Flat structure (0)")

    return ScoreComponent(
        name="Rent Potential",
        score=score,
        max_score=max_score,
        evidence=evidence
    )


def compute_gimlet_score(
    file_map: FileMap,
    identity: Identity,
    integration_plan: IntegrationPatchPlan | None,
    optimization_roadmap: OptimizationRoadmap | None
) -> GimletScore:
    """
    Compute complete GIMLET score (0-100).

    Component breakdown:
    - Integratability: 0-30
    - Rune-Fit: 0-30
    - Determinism Readiness: 0-20
    - Rent Potential: 0-20
    """
    integratability = _score_integratability(file_map, identity, integration_plan)
    rune_fit = _score_rune_fit(file_map, identity, optimization_roadmap)
    determinism_readiness = _score_determinism_readiness(file_map)
    rent_potential = _score_rent_potential(file_map, identity)

    total = (
        integratability.score +
        rune_fit.score +
        determinism_readiness.score +
        rent_potential.score
    )

    return GimletScore(
        total=total,
        integratability=integratability,
        rune_fit=rune_fit,
        determinism_readiness=determinism_readiness,
        rent_potential=rent_potential
    )
