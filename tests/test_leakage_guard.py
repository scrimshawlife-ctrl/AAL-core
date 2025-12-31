"""
Tests for leakage detection guards.
"""
import unittest
from engines.game_state.types import GameState
from engines.game_state.guards import assert_no_leakage


class TestLeakageGuard(unittest.TestCase):
    """Test leakage detection."""

    def test_clean_state_passes(self):
        """Verify clean state passes guard."""
        state = GameState(
            game_id="test_001",
            created_at="2025-01-01T00:00:00",
            context_key="abc123",
            applied_modifiers=[],
            internal_state={}
        )

        # Should not raise
        assert_no_leakage(state, "test_001")

    def test_game_id_mismatch_raises(self):
        """Verify mismatched game_id raises error."""
        state = GameState(
            game_id="test_001",
            created_at="2025-01-01T00:00:00",
            context_key="abc123",
            applied_modifiers=[],
            internal_state={}
        )

        with self.assertRaises(ValueError) as ctx:
            assert_no_leakage(state, "test_002")

        self.assertIn("Leakage detected", str(ctx.exception))
        self.assertIn("game_id", str(ctx.exception))

    def test_forbidden_key_prior_game_tempo_raises(self):
        """Verify forbidden key 'prior_game_tempo' raises error."""
        state = GameState(
            game_id="test_003",
            created_at="2025-01-01T00:00:00",
            context_key="abc123",
            applied_modifiers=[],
            internal_state={"prior_game_tempo": 98.5}
        )

        with self.assertRaises(ValueError) as ctx:
            assert_no_leakage(state, "test_003")

        self.assertIn("forbidden keys", str(ctx.exception))
        self.assertIn("prior_game_tempo", str(ctx.exception))

    def test_forbidden_key_carryover_raises(self):
        """Verify forbidden key 'carryover' raises error."""
        state = GameState(
            game_id="test_004",
            created_at="2025-01-01T00:00:00",
            context_key="abc123",
            applied_modifiers=[],
            internal_state={"carryover": {"some": "data"}}
        )

        with self.assertRaises(ValueError) as ctx:
            assert_no_leakage(state, "test_004")

        self.assertIn("forbidden keys", str(ctx.exception))
        self.assertIn("carryover", str(ctx.exception))

    def test_allowed_keys_pass(self):
        """Verify non-forbidden keys are allowed."""
        state = GameState(
            game_id="test_005",
            created_at="2025-01-01T00:00:00",
            context_key="abc123",
            applied_modifiers=[],
            internal_state={
                "current_tempo": 100.0,
                "active_lineups": ["lineup1"],
                "game_specific_data": {"foo": "bar"}
            }
        )

        # Should not raise
        assert_no_leakage(state, "test_005")

    def test_multiple_forbidden_keys_reported(self):
        """Verify multiple forbidden keys are detected."""
        state = GameState(
            game_id="test_006",
            created_at="2025-01-01T00:00:00",
            context_key="abc123",
            applied_modifiers=[],
            internal_state={
                "prior_game_tempo": 98.5,
                "last_game_id": "prev_game",
                "carryover": {}
            }
        )

        with self.assertRaises(ValueError) as ctx:
            assert_no_leakage(state, "test_006")

        error_msg = str(ctx.exception)
        self.assertIn("forbidden keys", error_msg)


if __name__ == "__main__":
    unittest.main()
