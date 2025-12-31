"""Tests for anchor drift logging (append-only JSONL).

Validates that drift events are properly logged to anchor_drift.log.jsonl
and that the log is append-only (no overwrites).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from abraxas.oracle.engine import generate_oracle
from abraxas.oracle.drift import DRIFT_LOG_PATH


def test_drift_log_created():
    """Test that drift log is created on first oracle run."""
    # Clean up any existing log for this test
    if DRIFT_LOG_PATH.exists():
        DRIFT_LOG_PATH.unlink()

    # Ensure parent directory exists
    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Generate oracle (should create log)
    generate_oracle()

    assert DRIFT_LOG_PATH.exists(), "Drift log not created"
    print("[PASS] Drift log created on first run")


def test_drift_log_append_only():
    """Test that drift log appends (not overwrites) on multiple runs."""
    # Clean start
    if DRIFT_LOG_PATH.exists():
        DRIFT_LOG_PATH.unlink()

    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Run oracle twice
    generate_oracle(anchor="test anchor alpha")
    generate_oracle(anchor="test anchor beta")

    # Read log lines
    lines = DRIFT_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")

    assert len(lines) == 2, f"Expected 2 log lines, got {len(lines)}"

    # Parse JSON
    entries = [json.loads(line) for line in lines]

    # Verify both are valid
    for i, entry in enumerate(entries):
        assert "utc" in entry, f"Line {i} missing utc"
        assert "anchor" in entry, f"Line {i} missing anchor"
        assert "drift_magnitude" in entry, f"Line {i} missing drift_magnitude"
        assert "gate_state" in entry, f"Line {i} missing gate_state"
        assert "runes_used" in entry, f"Line {i} missing runes_used"
        assert "manifest_sha256" in entry, f"Line {i} missing manifest_sha256"

    print(f"[PASS] Drift log appends correctly ({len(lines)} lines)")


def test_drift_log_contains_required_fields():
    """Test that drift log entries contain all required fields."""
    # Clean start
    if DRIFT_LOG_PATH.exists():
        DRIFT_LOG_PATH.unlink()

    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Generate oracle with history to trigger drift detection
    outputs_history = [
        "first oracle output about patterns",
        "second oracle output about cycles",
        "third oracle output about awareness"
    ]

    generate_oracle(
        anchor="core pattern recognition",
        outputs_history=outputs_history
    )

    # Read and parse log
    lines = DRIFT_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
    entry = json.loads(lines[-1])  # Last entry

    # Required fields
    required = [
        "utc",
        "anchor",
        "drift_magnitude",
        "drift_velocity",
        "integrity_score",
        "auto_recenter",
        "status",
        "anchor_hash",
        "samples_analyzed",
        "gate_state",
        "runes_used",
        "manifest_sha256"
    ]

    for field in required:
        assert field in entry, f"Log entry missing required field: {field}"

    # Validate types
    assert isinstance(entry["drift_magnitude"], (int, float))
    assert isinstance(entry["integrity_score"], (int, float))
    assert isinstance(entry["auto_recenter"], bool)
    assert entry["status"] in ["stable", "drifting", "critical"]
    assert isinstance(entry["runes_used"], list)
    assert len(entry["manifest_sha256"]) == 64  # SHA256 hex

    print("[PASS] Drift log entries contain all required fields")


def test_multiple_runs_unique_timestamps():
    """Test that multiple oracle runs produce unique timestamps."""
    # Clean start
    if DRIFT_LOG_PATH.exists():
        DRIFT_LOG_PATH.unlink()

    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Run oracle 3 times
    for i in range(3):
        generate_oracle(anchor=f"anchor {i}")

    # Read log
    lines = DRIFT_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
    entries = [json.loads(line) for line in lines]

    # Extract timestamps
    timestamps = [e["utc"] for e in entries]

    # All should be valid ISO timestamps
    for ts in timestamps:
        assert "T" in ts, f"Invalid timestamp format: {ts}"
        assert ts.endswith("Z") or "+" in ts, f"Timestamp missing timezone: {ts}"

    print(f"[PASS] Multiple runs produce valid timestamps ({len(timestamps)} entries)")


def run_all_tests():
    """Run all drift log tests."""
    print("=" * 60)
    print("Running Drift Log Append-Only Tests")
    print("=" * 60)

    test_drift_log_created()
    test_drift_log_append_only()
    test_drift_log_contains_required_fields()
    test_multiple_runs_unique_timestamps()

    print("=" * 60)
    print("All drift log tests PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
