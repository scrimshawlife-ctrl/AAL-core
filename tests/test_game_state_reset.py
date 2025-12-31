"""
Tests for game state reset and cold-start enforcement.
"""
import unittest
from engines.game_state.types import GameContext
from engines.game_state.reset import new_game_state


class TestGameStateReset(unittest.TestCase):
    """Test cold-start initialization."""

    def test_new_state_has_empty_internal_state(self):
        """Verify new state starts with empty internal_state."""
        ctx = GameContext(
            game_id="test_001",
            venue_id="TEST_ARENA",
            home_away="home",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-01"
        )

        state = new_game_state("test_001", ctx)

        self.assertEqual(state.internal_state, {})
        self.assertEqual(len(state.internal_state), 0)

    def test_new_state_has_correct_game_id(self):
        """Verify game_id is set correctly."""
        ctx = GameContext(
            game_id="test_002",
            venue_id="TEST_ARENA",
            home_away="away",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-02"
        )

        state = new_game_state("test_002", ctx)

        self.assertEqual(state.game_id, "test_002")

    def test_new_state_has_no_applied_modifiers(self):
        """Verify applied_modifiers starts empty."""
        ctx = GameContext(
            game_id="test_003",
            venue_id="TEST_ARENA",
            home_away="home",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-03"
        )

        state = new_game_state("test_003", ctx)

        self.assertEqual(state.applied_modifiers, [])

    def test_new_state_has_context_key(self):
        """Verify context_key is computed."""
        ctx = GameContext(
            game_id="test_004",
            venue_id="TEST_ARENA",
            home_away="home",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-04"
        )

        state = new_game_state("test_004", ctx)

        self.assertIsInstance(state.context_key, str)
        self.assertEqual(len(state.context_key), 64)  # SHA256 hex

    def test_multiple_resets_are_independent(self):
        """Verify each reset creates independent state."""
        ctx1 = GameContext(
            game_id="test_005",
            venue_id="ARENA_A",
            home_away="home",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-05"
        )

        ctx2 = GameContext(
            game_id="test_006",
            venue_id="ARENA_B",
            home_away="away",
            coach_id_home="coach_c",
            coach_id_away="coach_d",
            game_date="2025-01-06"
        )

        state1 = new_game_state("test_005", ctx1)
        state2 = new_game_state("test_006", ctx2)

        self.assertNotEqual(state1.game_id, state2.game_id)
        self.assertNotEqual(state1.context_key, state2.context_key)
        self.assertEqual(state1.internal_state, {})
        self.assertEqual(state2.internal_state, {})


if __name__ == "__main__":
    unittest.main()
