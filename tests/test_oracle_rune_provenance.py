"""Tests for Oracle ABX-Runes provenance stamping.

Validates that oracle outputs contain proper ABX-Runes provenance,
including manifest hashing, rune usage tracking, and gate state.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from abraxas.oracle.engine import generate_oracle
from abraxas.oracle.provenance import load_manifest_sha256


def test_oracle_contains_abx_runes_section():
    """Test that oracle output contains abx_runes provenance section."""
    output = generate_oracle()

    assert "abx_runes" in output, "Oracle output missing abx_runes section"

    abx = output["abx_runes"]
    assert "used" in abx, "abx_runes missing 'used' field"
    assert "manifest_sha256" in abx, "abx_runes missing manifest_sha256"
    assert "gate_state" in abx, "abx_runes missing gate_state"

    print("[PASS] Oracle output contains abx_runes section")


def test_manifest_sha256_stable():
    """Test that manifest SHA256 is stable across multiple calls."""
    hash1 = load_manifest_sha256()
    hash2 = load_manifest_sha256()

    assert hash1 == hash2, "Manifest hash not stable across calls"
    assert len(hash1) == 64, f"Manifest hash wrong length: {len(hash1)}"
    assert all(c in "0123456789abcdef" for c in hash1), "Manifest hash not hex"

    print(f"[PASS] Manifest SHA256 stable: {hash1[:16]}...")


def test_gate_state_valid():
    """Test that gate_state is one of the valid states."""
    valid_states = {"CLOSED", "LIMINAL", "OPEN"}

    # Test with different state vectors
    test_cases = [
        {"arousal": 0.2, "openness": 0.3},  # Should be CLOSED
        {"arousal": 0.5, "openness": 0.5},  # Should be LIMINAL
        {"arousal": 0.8, "openness": 0.9},  # Should be OPEN
    ]

    for i, state_vector in enumerate(test_cases):
        output = generate_oracle(state_vector=state_vector)
        gate_state = output["abx_runes"]["gate_state"]

        assert gate_state in valid_states, \
            f"Test case {i}: Invalid gate_state '{gate_state}'"

    print("[PASS] Gate states valid across test cases")


def test_runes_used_includes_required():
    """Test that runes_used includes ϟ₄, ϟ₅, ϟ₆ for deep oracles."""
    state_vector = {"arousal": 0.8, "openness": 0.9}  # OPEN gate
    output = generate_oracle(state_vector=state_vector, requested_depth="deep")

    runes_used = output["abx_runes"]["used"]

    # For non-grounding outputs, should include SDS, IPL, ADD
    required_runes = {"ϟ₄", "ϟ₅", "ϟ₆"}
    runes_set = set(runes_used)

    assert required_runes.issubset(runes_set), \
        f"Missing required runes. Expected {required_runes}, got {runes_set}"

    # Should also include structural runes
    assert "ϟ₁" in runes_set, "Missing SEED rune (ϟ₁)"
    assert "ϟ₂" in runes_set, "Missing CANON rune (ϟ₂)"

    print(f"[PASS] Runes used includes required: {runes_used}")


def test_deterministic_output_with_same_inputs():
    """Test that same inputs produce same output."""
    state_vector = {"arousal": 0.6, "valence": 0.7, "cognitive_load": 0.4, "openness": 0.65}
    context = {"time_of_day": "evening", "session_count": 2}

    output1 = generate_oracle(
        state_vector=state_vector,
        context=context,
        requested_depth="shallow"
    )

    output2 = generate_oracle(
        state_vector=state_vector,
        context=context,
        requested_depth="shallow"
    )

    # Core fields should match
    assert output1["depth"] == output2["depth"]
    assert output1["text"] == output2["text"]
    assert output1["abx_runes"]["gate_state"] == output2["abx_runes"]["gate_state"]
    assert output1["abx_runes"]["manifest_sha256"] == output2["abx_runes"]["manifest_sha256"]

    # Susceptibility score should be deterministic
    sus1 = output1["abx_runes"]["susceptibility_score"]
    sus2 = output2["abx_runes"]["susceptibility_score"]
    assert sus1 == sus2, f"Susceptibility not deterministic: {sus1} vs {sus2}"

    print("[PASS] Deterministic output with same inputs")


def test_grounding_output_minimal_runes():
    """Test that grounding outputs use minimal rune set."""
    # Force CLOSED gate
    state_vector = {"arousal": 0.1, "openness": 0.1, "cognitive_load": 0.9}
    output = generate_oracle(state_vector=state_vector, requested_depth="deep")

    # Should get grounding despite requesting deep
    assert output["depth"] == "grounding"

    # Should only use structural + SDS runes, not IPL/ADD
    runes_used = set(output["abx_runes"]["used"])
    assert runes_used == {"ϟ₁", "ϟ₂", "ϟ₄"}, \
        f"Grounding should use minimal runes, got {runes_used}"

    print("[PASS] Grounding output uses minimal rune set")


def run_all_tests():
    """Run all provenance tests."""
    print("=" * 60)
    print("Running Oracle ABX-Runes Provenance Tests")
    print("=" * 60)

    test_oracle_contains_abx_runes_section()
    test_manifest_sha256_stable()
    test_gate_state_valid()
    test_runes_used_includes_required()
    test_deterministic_output_with_same_inputs()
    test_grounding_output_minimal_runes()

    print("=" * 60)
    print("All provenance tests PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
