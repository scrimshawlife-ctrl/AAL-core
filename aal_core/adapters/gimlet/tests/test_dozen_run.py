"""
AAL-GIMLET Dozen-Run Stability Test
Verify 12 consecutive runs produce identical results (invariance gate).
"""

import pytest
from pathlib import Path


from aal_core.adapters.gimlet import inspect


@pytest.fixture
def stable_codebase(tmp_path):
    """Create a stable test codebase"""
    # Create Python package
    pkg = tmp_path / "stable_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("# Stable package\n")
    (pkg / "core.py").write_text("def main():\n    return 'stable'\n")

    # Create tests
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text("def test_main():\n    assert True\n")

    # Create config
    (tmp_path / "config.yaml").write_text("key: value\n")

    return str(tmp_path)


def test_dozen_run_invariance(stable_codebase):
    """
    Dozen-Run Stability Simulation (invariance gate).

    Requirement: 12 consecutive runs with same seed produce identical results.
    This is the canonical stability test for AAL-core.
    """
    seed = "dozen-run-stability-seed"
    num_runs = 12

    results = []
    for run_num in range(num_runs):
        result = inspect(stable_codebase, mode="inspect", run_seed=seed)
        results.append(result)

    # Extract manifest hashes (deterministic fingerprint)
    manifest_hashes = [r["abx_runes"]["manifest_sha256"] for r in results]

    # ALL hashes must be identical
    unique_hashes = set(manifest_hashes)
    assert len(unique_hashes) == 1, \
        f"Dozen-run failed: got {len(unique_hashes)} unique hashes instead of 1"

    # Verify specific components are identical across all runs
    for i in range(1, num_runs):
        # Check artifact hash
        assert results[0]["result"]["provenance"]["artifact_hash"] == \
               results[i]["result"]["provenance"]["artifact_hash"], \
            f"Run {i}: artifact_hash differs"

        # Check identity classification
        assert results[0]["result"]["identity"]["kind"] == \
               results[i]["result"]["identity"]["kind"], \
            f"Run {i}: identity kind differs"

        assert results[0]["result"]["identity"]["confidence"] == \
               results[i]["result"]["identity"]["confidence"], \
            f"Run {i}: identity confidence differs"

        # Check score totals
        assert results[0]["result"]["score"]["total"] == \
               results[i]["result"]["score"]["total"], \
            f"Run {i}: total score differs"

        # Check all score components
        for component in ["integratability", "rune_fit", "determinism_readiness", "rent_potential"]:
            assert results[0]["result"]["score"][component]["score"] == \
                   results[i]["result"]["score"][component]["score"], \
                f"Run {i}: {component} score differs"


def test_dozen_run_file_map_stability(stable_codebase):
    """FileMap remains stable across dozen runs"""
    seed = "filemap-stability"
    num_runs = 12

    file_maps = []
    for _ in range(num_runs):
        result = inspect(stable_codebase, run_seed=seed)
        file_maps.append(result["result"]["file_map"])

    # All file maps should be identical
    for i in range(1, num_runs):
        assert file_maps[0]["file_count"] == file_maps[i]["file_count"]
        assert file_maps[0]["total_size_bytes"] == file_maps[i]["total_size_bytes"]
        assert file_maps[0]["languages"] == file_maps[i]["languages"]
        assert file_maps[0]["entrypoints"] == file_maps[i]["entrypoints"]

        # Check file-by-file
        for j, (f0, fi) in enumerate(zip(file_maps[0]["files"], file_maps[i]["files"])):
            assert f0["path"] == fi["path"], f"Run {i}, file {j}: path differs"
            assert f0["sha256"] == fi["sha256"], f"Run {i}, file {j}: hash differs"
            assert f0["size_bytes"] == fi["size_bytes"], f"Run {i}, file {j}: size differs"


def test_dozen_run_evidence_stability(stable_codebase):
    """Evidence remains stable across dozen runs"""
    seed = "evidence-stability"
    num_runs = 12

    evidence_lists = []
    for _ in range(num_runs):
        result = inspect(stable_codebase, run_seed=seed)
        evidence_lists.append(result["result"]["identity"]["evidence"])

    # Evidence should be identical across all runs
    for i in range(1, num_runs):
        assert len(evidence_lists[0]) == len(evidence_lists[i]), \
            f"Run {i}: evidence count differs"

        for j, (e0, ei) in enumerate(zip(evidence_lists[0], evidence_lists[i])):
            assert e0["file_path"] == ei["file_path"], \
                f"Run {i}, evidence {j}: file_path differs"
            assert e0["rule_hit"] == ei["rule_hit"], \
                f"Run {i}, evidence {j}: rule_hit differs"
            assert e0["confidence_contribution"] == ei["confidence_contribution"], \
                f"Run {i}, evidence {j}: confidence differs"


def test_dozen_run_with_different_seeds():
    """Different seeds produce different provenance but same analysis"""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "test.py").write_text("print('test')\n")

        # Run with different seeds
        seeds = [f"seed-{i}" for i in range(12)]
        results = [inspect(str(tmp_path), run_seed=seed) for seed in seeds]

        # Provenances should differ (different seeds)
        provenance_seeds = [r["result"]["provenance"]["run_seed"] for r in results]
        assert len(set(provenance_seeds)) == 12, "All seeds should be unique"

        # But core analysis should be identical
        identity_kinds = [r["result"]["identity"]["kind"] for r in results]
        assert len(set(identity_kinds)) == 1, "Identity classification should be same"

        total_scores = [r["result"]["score"]["total"] for r in results]
        assert len(set(total_scores)) == 1, "Total scores should be same"


def test_dozen_run_integration_plan_stability(tmp_path):
    """Integration plan remains stable across dozen runs"""
    # Create AAL subsystem structure
    aal_core = tmp_path / "aal_core"
    aal_core.mkdir()
    (aal_core / "__init__.py").write_text("")
    (aal_core / "module.py").write_text("def func():\n    pass\n")

    seed = "integration-stability"
    num_runs = 12

    plans = []
    for _ in range(num_runs):
        result = inspect(str(tmp_path), mode="integrate", run_seed=seed)
        plans.append(result["result"]["integration_plan"])

    # All plans should be identical
    for i in range(1, num_runs):
        if plans[0] is None:
            assert plans[i] is None
        else:
            assert len(plans[0]["issues"]) == len(plans[i]["issues"])
            assert plans[0]["auto_fixable"] == plans[i]["auto_fixable"]
            assert plans[0]["estimated_complexity"] == plans[i]["estimated_complexity"]


def test_dozen_run_optimization_roadmap_stability(tmp_path):
    """Optimization roadmap remains stable across dozen runs"""
    # Create external codebase
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "utils.py").write_text("def helper():\n    pass\n")

    seed = "roadmap-stability"
    num_runs = 12

    roadmaps = []
    for _ in range(num_runs):
        result = inspect(str(tmp_path), mode="optimize", run_seed=seed)
        roadmaps.append(result["result"]["optimization_roadmap"])

    # All roadmaps should be identical
    for i in range(1, num_runs):
        assert roadmaps[0]["total_phases"] == roadmaps[i]["total_phases"]
        assert len(roadmaps[0]["phases"]) == len(roadmaps[i]["phases"])

        for j, (p0, pi) in enumerate(zip(roadmaps[0]["phases"], roadmaps[i]["phases"])):
            assert p0["phase_number"] == pi["phase_number"]
            assert p0["name"] == pi["name"]
            assert p0["estimated_effort"] == pi["estimated_effort"]
