"""
AAL-GIMLET Missing Input Tests
Verify proper error handling for invalid/missing inputs.
"""

import pytest
from pathlib import Path

from aal_core.adapters.gimlet import inspect, normalize_input
from aal_core.adapters.gimlet.contracts import InspectMode


def test_nonexistent_path():
    """Nonexistent path raises ValueError"""
    with pytest.raises(ValueError, match="source_path must be directory or .zip file"):
        inspect("/nonexistent/path/to/nowhere")


def test_invalid_mode():
    """Invalid mode raises ValueError"""
    with pytest.raises(ValueError, match="Invalid mode"):
        inspect(".", mode="invalid_mode")


def test_file_not_zip(tmp_path):
    """Non-zip file raises ValueError"""
    text_file = tmp_path / "test.txt"
    text_file.write_text("not a zip")

    with pytest.raises(ValueError, match="source_path must be directory or .zip file"):
        inspect(str(text_file))


def test_empty_directory(tmp_path):
    """Empty directory produces valid result with zero files"""
    result = inspect(str(tmp_path), run_seed="empty-test")

    assert result["result"]["file_map"]["file_count"] == 0
    assert result["result"]["file_map"]["total_size_bytes"] == 0
    assert result["result"]["identity"]["kind"] == "EXTERNAL"  # No AAL patterns


def test_score_bounds_with_minimal_input(tmp_path):
    """Minimal input still produces valid bounded scores"""
    # Create single file
    (tmp_path / "lonely.py").write_text("print('hello')\n")

    result = inspect(str(tmp_path), run_seed="minimal")
    score = result["result"]["score"]

    # All scores should be valid even with minimal input
    assert 0.0 <= score["total"] <= 100.0
    assert 0.0 <= score["integratability"]["score"] <= 30.0
    assert 0.0 <= score["rune_fit"]["score"] <= 30.0


def test_confidence_requires_evidence():
    """Non-zero confidence requires evidence (contract validation)"""
    from aal_core.adapters.gimlet.contracts import Identity, IdentityKind

    # This should raise ValueError
    with pytest.raises(ValueError, match="Non-zero confidence requires evidence"):
        Identity(
            kind=IdentityKind.EXTERNAL,
            confidence=0.5,
            evidence=[]  # Empty evidence with non-zero confidence
        )


def test_invalid_confidence_bounds():
    """Confidence outside [0, 1] raises ValueError"""
    from aal_core.adapters.gimlet.contracts import Identity, IdentityKind, Evidence

    # confidence > 1.0
    with pytest.raises(ValueError, match="confidence must be in"):
        Identity(
            kind=IdentityKind.EXTERNAL,
            confidence=1.5,
            evidence=[Evidence("test.py", "test", 0.5)]
        )

    # confidence < 0.0
    with pytest.raises(ValueError, match="confidence must be in"):
        Identity(
            kind=IdentityKind.EXTERNAL,
            confidence=-0.1,
            evidence=[Evidence("test.py", "test", 0.1)]
        )


def test_score_component_bounds_validation():
    """ScoreComponent validates score <= max_score"""
    from aal_core.adapters.gimlet.contracts import ScoreComponent

    # Valid: score within bounds
    valid = ScoreComponent(
        name="Test",
        score=15.0,
        max_score=30.0,
        evidence=["test"]
    )
    assert valid.score == 15.0

    # Invalid: score exceeds max_score
    with pytest.raises(ValueError, match="score .* out of bounds"):
        ScoreComponent(
            name="Test",
            score=35.0,
            max_score=30.0,
            evidence=["test"]
        )


def test_gimlet_score_total_validation():
    """GimletScore validates total equals sum of components"""
    from aal_core.adapters.gimlet.contracts import GimletScore, ScoreComponent

    integratability = ScoreComponent("Integratability", 10.0, 30.0, ["test"])
    rune_fit = ScoreComponent("Rune-Fit", 10.0, 30.0, ["test"])
    determinism = ScoreComponent("Determinism", 10.0, 20.0, ["test"])
    rent = ScoreComponent("Rent", 10.0, 20.0, ["test"])

    # Valid: total matches sum
    valid = GimletScore(
        total=40.0,
        integratability=integratability,
        rune_fit=rune_fit,
        determinism_readiness=determinism,
        rent_potential=rent
    )
    assert valid.total == 40.0

    # Invalid: total doesn't match sum
    with pytest.raises(ValueError, match="total .* != sum of components"):
        GimletScore(
            total=50.0,  # Wrong!
            integratability=integratability,
            rune_fit=rune_fit,
            determinism_readiness=determinism,
            rent_potential=rent
        )


def test_optimization_roadmap_phase_count_validation():
    """OptimizationRoadmap validates phases length matches total_phases"""
    from aal_core.adapters.gimlet.contracts import OptimizationRoadmap, OptimizationPhase

    phases = [
        OptimizationPhase(0, "Phase 0", "desc", ["action"], ["rune"], "low"),
        OptimizationPhase(1, "Phase 1", "desc", ["action"], ["rune"], "medium"),
    ]

    # Valid
    valid = OptimizationRoadmap(
        phases=phases,
        total_phases=2,
        summary="test"
    )
    assert valid.total_phases == 2

    # Invalid: mismatch
    with pytest.raises(ValueError, match="phases length .* != total_phases"):
        OptimizationRoadmap(
            phases=phases,
            total_phases=3,  # Wrong!
            summary="test"
        )


def test_acronym_definition_alias_validation():
    """AcronymDefinition validates alias_for consistency"""
    from aal_core.adapters.gimlet.contracts import AcronymDefinition

    # Invalid: alias status without alias_for
    with pytest.raises(ValueError, match="Alias status requires alias_for"):
        AcronymDefinition(
            canonical_name="TEST",
            expansion="Test",
            functional_definition="Test",
            status="alias",
            alias_for=None  # Missing!
        )

    # Invalid: alias_for without alias status
    with pytest.raises(ValueError, match="alias_for only valid for alias status"):
        AcronymDefinition(
            canonical_name="TEST",
            expansion="Test",
            functional_definition="Test",
            status="active",
            alias_for="OTHER"  # Shouldn't be present!
        )
