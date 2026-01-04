"""
AAL-GIMLET Planning Module
Integration and optimization planning.
"""

from typing import List, Optional

from .contracts import (
    FileMap,
    Identity,
    IdentityKind,
    IntegrationPatchPlan,
    IntegrationIssue,
    OptimizationRoadmap,
    OptimizationPhase,
)


def _scan_for_integration_issues(file_map: FileMap, identity: Identity) -> List[IntegrationIssue]:
    """Scan AAL-native code for integration issues"""
    issues = []

    # Check for test coverage
    has_tests = any("test_" in f.path or f.path.startswith("tests/") for f in file_map.files)
    if not has_tests:
        issues.append(IntegrationIssue(
            severity="warning",
            category="missing_test",
            file_path=None,
            message="No test files detected (test_*.py or tests/ directory)",
            suggested_fix="Add pytest-based tests following AAL-core conventions"
        ))

    # Check for __init__.py in Python packages
    python_dirs = set()
    init_files = set()

    for f in file_map.files:
        if f.language == "python":
            parts = f.path.split("/")
            if len(parts) > 1:
                for i in range(1, len(parts)):
                    python_dirs.add("/".join(parts[:i]))
        if f.path.endswith("__init__.py"):
            init_files.add("/".join(f.path.split("/")[:-1]))

    missing_inits = python_dirs - init_files
    for missing in sorted(missing_inits):
        if not missing.startswith(".") and not missing.startswith("tests"):
            issues.append(IntegrationIssue(
                severity="error",
                category="broken_boundary",
                file_path=f"{missing}/__init__.py",
                message=f"Missing __init__.py in Python package: {missing}",
                suggested_fix=f"Create {missing}/__init__.py"
            ))

    # Check for naming violations (non-snake_case Python modules)
    for f in file_map.files:
        if f.language == "python" and f.path.endswith(".py"):
            module_name = f.path.split("/")[-1].replace(".py", "")
            if module_name and module_name != module_name.lower():
                if "_" not in module_name or module_name != module_name.replace("-", "_"):
                    issues.append(IntegrationIssue(
                        severity="warning",
                        category="naming_violation",
                        file_path=f.path,
                        message=f"Non-canonical Python module name: {module_name}",
                        suggested_fix=f"Rename to snake_case: {module_name.lower()}"
                    ))

    return issues


def build_integration_plan(file_map: FileMap, identity: Identity) -> Optional[IntegrationPatchPlan]:
    """
    Build integration plan for AAL-native code.

    Returns:
        IntegrationPatchPlan if identity is AAL_OVERLAY or AAL_SUBSYSTEM, else None
    """
    if identity.kind == IdentityKind.EXTERNAL:
        return None

    issues = _scan_for_integration_issues(file_map, identity)

    # Build action items
    actions = []
    auto_fixable = True

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    if error_count > 0:
        actions.append(f"Fix {error_count} critical error(s)")
        auto_fixable = False  # Structural errors need manual review

    if warning_count > 0:
        actions.append(f"Address {warning_count} warning(s)")

    if not issues:
        actions.append("No integration issues detected")

    # Add standard integration actions
    if identity.kind == IdentityKind.AAL_OVERLAY:
        actions.append("Validate overlay manifest against yggdrasil-overlay/0.1 schema")
        actions.append("Register overlay with AAL-core registry")
    elif identity.kind == IdentityKind.AAL_SUBSYSTEM:
        actions.append("Validate subsystem boundaries and imports")
        actions.append("Ensure acronym definition exists in registry")

    # Estimate complexity
    if error_count > 5 or warning_count > 10:
        complexity = "high"
    elif error_count > 0 or warning_count > 3:
        complexity = "moderate"
    else:
        complexity = "trivial"

    return IntegrationPatchPlan(
        issues=issues,
        actions=actions,
        auto_fixable=auto_fixable,
        estimated_complexity=complexity
    )


def build_optimization_roadmap(file_map: FileMap) -> OptimizationRoadmap:
    """
    Build canonical optimization roadmap for external code.

    Returns standard 3-phase roadmap:
    - Phase 0: Instrumentation + provenance
    - Phase 1: Rune façade (non-invasive)
    - Phase 2: Internal modularization (rent-gated)
    """

    # Phase 0: Instrumentation
    phase0_actions = [
        "Add deterministic input/output logging",
        "Implement provenance envelope for all operations",
        "Create baseline performance metrics",
        "Add entropy source tracking (SEED compatibility)",
    ]

    phase0_runes = [
        "external.v0.instrument",
        "external.v0.provenance",
    ]

    # Phase 1: Rune façade
    phase1_actions = [
        "Identify stable API boundaries",
        "Create ABX-Runes façade layer (non-invasive)",
        "Implement rune attachment for provenance",
        "Add integration tests with AAL-core EventBus",
    ]

    phase1_runes = [
        "external.v0.facade",
        "external.v0.bridge",
    ]

    # Detect candidate subsystems for Phase 2
    candidate_modules = []
    seen_dirs = set()
    for f in file_map.files:
        parts = f.path.split("/")
        if len(parts) > 1 and f.language in ["python", "javascript", "typescript"]:
            top_level = parts[0]
            if top_level not in seen_dirs and not top_level.startswith("."):
                seen_dirs.add(top_level)
                candidate_modules.append(top_level)

    phase2_actions = [
        "Analyze subsystem boundaries (candidates: {})".format(", ".join(sorted(candidate_modules)[:5])),
        "Apply complexity rent analysis",
        "Extract high-value subsystems as canonical modules",
        "Implement deterministic module registry",
        "Add dozen-run stability tests",
    ]

    phase2_runes = [
        "external.v0.modularize",
        "external.v0.stabilize",
    ]

    phases = [
        OptimizationPhase(
            phase_number=0,
            name="Instrumentation + Provenance",
            description="Add observability and determinism foundations",
            actions=phase0_actions,
            candidate_runes=phase0_runes,
            estimated_effort="low"
        ),
        OptimizationPhase(
            phase_number=1,
            name="Rune Façade (Non-Invasive)",
            description="Create ABX-Runes integration layer without internal changes",
            actions=phase1_actions,
            candidate_runes=phase1_runes,
            estimated_effort="medium"
        ),
        OptimizationPhase(
            phase_number=2,
            name="Internal Modularization (Rent-Gated)",
            description="Refactor internal structure only where complexity pays rent",
            actions=phase2_actions,
            candidate_runes=phase2_runes,
            estimated_effort="high"
        ),
    ]

    summary = (
        f"External codebase with {file_map.file_count} files ({', '.join(file_map.languages)}). "
        f"Recommended 3-phase integration: instrumentation -> façade -> selective modularization."
    )

    return OptimizationRoadmap(
        phases=phases,
        total_phases=len(phases),
        summary=summary
    )
