"""
AAL-GIMLET Bounds Tests
Verify all scores stay within valid bounds.
"""

import pytest
from pathlib import Path

from aal_core.adapters.gimlet import inspect


@pytest.fixture
def minimal_codebase(tmp_path):
    """Minimal codebase with one file"""
    (tmp_path / "main.py").write_text("print('hello')\n")
    return str(tmp_path)


@pytest.fixture
def large_codebase(tmp_path):
    """Large codebase with many files"""
    # Create package structure
    pkg = tmp_path / "my_package"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    # Create multiple modules
    for i in range(20):
        (pkg / f"module_{i}.py").write_text(f"def func_{i}():\n    return {i}\n")

    # Create tests
    tests = tmp_path / "tests"
    tests.mkdir()
    for i in range(10):
        (tests / f"test_{i}.py").write_text(f"def test_{i}():\n    assert True\n")

    # Create config files
    (tmp_path / "config.yaml").write_text("setting: value\n")
    (tmp_path / "setup.py").write_text("from setuptools import setup\n")

    return str(tmp_path)


@pytest.fixture
def aal_subsystem_codebase(tmp_path):
    """Codebase that looks like AAL subsystem"""
    # Create aal_core structure
    aal_core = tmp_path / "aal_core"
    aal_core.mkdir()
    (aal_core / "__init__.py").write_text("")

    alignment = aal_core / "alignment"
    alignment.mkdir()
    (alignment / "__init__.py").write_text("")
    (alignment / "governor.py").write_text("class Governor:\n    pass\n")

    # Create tests
    tests = tmp_path / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_alignment.py").write_text("def test_governor():\n    assert True\n")

    return str(tmp_path)


def test_total_score_bounds(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Total score always in [0, 100]"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        total = result["result"]["score"]["total"]

        assert 0.0 <= total <= 100.0, f"Total score {total} out of bounds [0, 100]"


def test_integratability_bounds(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Integratability score always in [0, 30]"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        score = result["result"]["score"]["integratability"]["score"]
        max_score = result["result"]["score"]["integratability"]["max_score"]

        assert max_score == 30.0, "Integratability max_score must be 30"
        assert 0.0 <= score <= 30.0, f"Integratability {score} out of bounds [0, 30]"


def test_rune_fit_bounds(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Rune-Fit score always in [0, 30]"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        score = result["result"]["score"]["rune_fit"]["score"]
        max_score = result["result"]["score"]["rune_fit"]["max_score"]

        assert max_score == 30.0, "Rune-Fit max_score must be 30"
        assert 0.0 <= score <= 30.0, f"Rune-Fit {score} out of bounds [0, 30]"


def test_determinism_readiness_bounds(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Determinism Readiness score always in [0, 20]"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        score = result["result"]["score"]["determinism_readiness"]["score"]
        max_score = result["result"]["score"]["determinism_readiness"]["max_score"]

        assert max_score == 20.0, "Determinism Readiness max_score must be 20"
        assert 0.0 <= score <= 20.0, f"Determinism Readiness {score} out of bounds [0, 20]"


def test_rent_potential_bounds(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Rent Potential score always in [0, 20]"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        score = result["result"]["score"]["rent_potential"]["score"]
        max_score = result["result"]["score"]["rent_potential"]["max_score"]

        assert max_score == 20.0, "Rent Potential max_score must be 20"
        assert 0.0 <= score <= 20.0, f"Rent Potential {score} out of bounds [0, 20]"


def test_component_sum_equals_total(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Sum of component scores equals total score"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        score_obj = result["result"]["score"]

        component_sum = (
            score_obj["integratability"]["score"] +
            score_obj["rune_fit"]["score"] +
            score_obj["determinism_readiness"]["score"] +
            score_obj["rent_potential"]["score"]
        )

        total = score_obj["total"]

        assert abs(component_sum - total) < 0.01, \
            f"Component sum {component_sum} != total {total}"


def test_confidence_bounds(minimal_codebase, large_codebase, aal_subsystem_codebase):
    """Identity confidence always in [0, 1]"""
    codebases = [minimal_codebase, large_codebase, aal_subsystem_codebase]

    for codebase in codebases:
        result = inspect(codebase, run_seed="bounds-test")
        confidence = result["result"]["identity"]["confidence"]

        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of bounds [0, 1]"


def test_evidence_contribution_bounds(aal_subsystem_codebase):
    """Evidence contributions are in [0, 1]"""
    result = inspect(aal_subsystem_codebase, run_seed="bounds-test")
    evidence_list = result["result"]["identity"]["evidence"]

    for evidence in evidence_list:
        contrib = evidence["confidence_contribution"]
        assert 0.0 <= contrib <= 1.0, \
            f"Evidence contribution {contrib} out of bounds [0, 1]"


def test_score_evidence_is_list(minimal_codebase):
    """All score components have evidence as list"""
    result = inspect(minimal_codebase, run_seed="bounds-test")
    score_obj = result["result"]["score"]

    components = ["integratability", "rune_fit", "determinism_readiness", "rent_potential"]

    for comp_name in components:
        comp = score_obj[comp_name]
        assert isinstance(comp["evidence"], list), \
            f"{comp_name} evidence must be a list"
        assert len(comp["evidence"]) > 0, \
            f"{comp_name} evidence must not be empty"


def test_file_map_consistency(large_codebase):
    """FileMap counts are consistent"""
    result = inspect(large_codebase, run_seed="bounds-test")
    file_map = result["result"]["file_map"]

    # file_count should match length of files array
    assert file_map["file_count"] == len(file_map["files"]), \
        "file_count must match files array length"

    # total_size_bytes should match sum of file sizes
    total_size = sum(f["size_bytes"] for f in file_map["files"])
    assert file_map["total_size_bytes"] == total_size, \
        "total_size_bytes must match sum of file sizes"

    # All sizes should be non-negative
    for f in file_map["files"]:
        assert f["size_bytes"] >= 0, "File size cannot be negative"


def test_languages_are_unique_and_sorted(large_codebase):
    """FileMap languages are unique and sorted"""
    result = inspect(large_codebase, run_seed="bounds-test")
    languages = result["result"]["file_map"]["languages"]

    # Should be unique
    assert len(languages) == len(set(languages)), \
        "Languages list should not have duplicates"

    # Should be sorted
    assert languages == sorted(languages), \
        "Languages list should be sorted"


def test_entrypoints_are_sorted(large_codebase):
    """FileMap entrypoints are sorted"""
    result = inspect(large_codebase, run_seed="bounds-test")
    entrypoints = result["result"]["file_map"]["entrypoints"]

    assert entrypoints == sorted(entrypoints), \
        "Entrypoints list should be sorted"


def test_phase_numbers_are_sequential():
    """Optimization roadmap phase numbers are sequential"""
    from aal_core.adapters.gimlet.plan import build_optimization_roadmap
    from aal_core.adapters.gimlet.contracts import FileMap, FileInfo

    # Create minimal file map
    file_map = FileMap(
        files=[FileInfo("test.py", "abc123", 100, "python", False)],
        total_size_bytes=100,
        file_count=1,
        languages=["python"],
        entrypoints=[]
    )

    roadmap = build_optimization_roadmap(file_map)

    for i, phase in enumerate(roadmap.phases):
        assert phase.phase_number == i, \
            f"Phase number should be {i}, got {phase.phase_number}"


def test_integration_issue_severity_is_valid(aal_subsystem_codebase):
    """Integration issues have valid severity levels"""
    result = inspect(aal_subsystem_codebase, mode="integrate", run_seed="bounds-test")
    integration_plan = result["result"]["integration_plan"]

    if integration_plan and integration_plan["issues"]:
        valid_severities = {"error", "warning", "info"}
        for issue in integration_plan["issues"]:
            assert issue["severity"] in valid_severities, \
                f"Invalid severity: {issue['severity']}"
