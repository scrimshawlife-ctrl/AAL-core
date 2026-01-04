"""
AAL-GIMLET Determinism Tests
Verify same inputs produce same outputs.
"""

import pytest
import tempfile
import os
from pathlib import Path

from aal_core.adapters.gimlet import inspect, normalize_input
from aal_core.adapters.gimlet.contracts import InspectMode


@pytest.fixture
def sample_codebase(tmp_path):
    """Create a minimal sample codebase"""
    # Create Python package structure
    pkg_dir = tmp_path / "sample_pkg"
    pkg_dir.mkdir()

    (pkg_dir / "__init__.py").write_text("# Sample package\n")
    (pkg_dir / "module_a.py").write_text("def foo():\n    return 42\n")
    (pkg_dir / "module_b.py").write_text("def bar():\n    return 'hello'\n")

    # Create tests directory
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_module_a.py").write_text("def test_foo():\n    assert True\n")

    return str(tmp_path)


def test_inspect_determinism_same_seed(sample_codebase):
    """Same input with same seed produces identical results"""
    seed = "deterministic-seed-123"

    result1 = inspect(sample_codebase, mode="inspect", run_seed=seed)
    result2 = inspect(sample_codebase, mode="inspect", run_seed=seed)

    # Compare manifest hashes (deterministic fingerprint)
    hash1 = result1["abx_runes"]["manifest_sha256"]
    hash2 = result2["abx_runes"]["manifest_sha256"]

    assert hash1 == hash2, "Same seed should produce identical manifest hash"

    # Compare artifact hashes
    artifact1 = result1["result"]["provenance"]["artifact_hash"]
    artifact2 = result2["result"]["provenance"]["artifact_hash"]

    assert artifact1 == artifact2, "Same input should produce identical artifact hash"


def test_normalize_input_determinism(sample_codebase):
    """FileMap normalization is deterministic"""
    file_map1, prov1, temp1 = normalize_input(sample_codebase, InspectMode.INSPECT, run_seed="test")
    file_map2, prov2, temp2 = normalize_input(sample_codebase, InspectMode.INSPECT, run_seed="test")

    # Compare file counts
    assert file_map1.file_count == file_map2.file_count

    # Compare file paths (should be in same order)
    paths1 = [f.path for f in file_map1.files]
    paths2 = [f.path for f in file_map2.files]
    assert paths1 == paths2, "File paths should be in deterministic order"

    # Compare hashes
    hashes1 = [f.sha256 for f in file_map1.files]
    hashes2 = [f.sha256 for f in file_map2.files]
    assert hashes1 == hashes2, "File hashes should match"


def test_score_determinism(sample_codebase):
    """Scoring is deterministic for same input"""
    result1 = inspect(sample_codebase, mode="inspect", run_seed="score-test")
    result2 = inspect(sample_codebase, mode="inspect", run_seed="score-test")

    score1 = result1["result"]["score"]
    score2 = result2["result"]["score"]

    assert score1["total"] == score2["total"]
    assert score1["integratability"]["score"] == score2["integratability"]["score"]
    assert score1["rune_fit"]["score"] == score2["rune_fit"]["score"]
    assert score1["determinism_readiness"]["score"] == score2["determinism_readiness"]["score"]
    assert score1["rent_potential"]["score"] == score2["rent_potential"]["score"]


def test_identity_classification_determinism(sample_codebase):
    """Identity classification is deterministic"""
    result1 = inspect(sample_codebase, run_seed="identity-test")
    result2 = inspect(sample_codebase, run_seed="identity-test")

    id1 = result1["result"]["identity"]
    id2 = result2["result"]["identity"]

    assert id1["kind"] == id2["kind"]
    assert id1["confidence"] == id2["confidence"]
    assert len(id1["evidence"]) == len(id2["evidence"])


def test_file_ordering_independence(tmp_path):
    """Results are independent of filesystem traversal order"""
    # Create files with names that might sort differently
    files = ["zebra.py", "alpha.py", "middle.py", "123_numeric.py"]

    for filename in files:
        (tmp_path / filename).write_text(f"# {filename}\n")

    result1 = inspect(str(tmp_path), run_seed="order-test")
    result2 = inspect(str(tmp_path), run_seed="order-test")

    # Should get same hash regardless of OS filesystem ordering
    assert result1["abx_runes"]["manifest_sha256"] == result2["abx_runes"]["manifest_sha256"]


def test_provenance_includes_seed(sample_codebase):
    """Provenance envelope includes run_seed"""
    seed = "test-seed-456"
    result = inspect(sample_codebase, run_seed=seed)

    assert result["abx_runes"]["provenance"]["run_seed"] == seed
    assert result["result"]["provenance"]["run_seed"] == seed


def test_different_seeds_different_provenance(sample_codebase):
    """Different seeds produce different provenance but same analysis"""
    result1 = inspect(sample_codebase, run_seed="seed-a")
    result2 = inspect(sample_codebase, run_seed="seed-b")

    # Provenance should differ
    assert result1["result"]["provenance"]["run_seed"] != result2["result"]["provenance"]["run_seed"]

    # But core analysis should be identical
    assert result1["result"]["identity"]["kind"] == result2["result"]["identity"]["kind"]
    assert result1["result"]["score"]["total"] == result2["result"]["score"]["total"]
