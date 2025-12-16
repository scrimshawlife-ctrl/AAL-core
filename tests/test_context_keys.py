"""
Tests for context key building and hashing stability.
"""
import unittest
from engines.game_state.types import GameContext
from engines.game_state.context_keys import build_context_key, hash_key


class TestContextKeys(unittest.TestCase):
    """Test context key generation and hashing."""

    def test_build_context_key_includes_required_fields(self):
        """Verify all required fields are in context key."""
        ctx = GameContext(
            game_id="test_001",
            venue_id="MSG",
            home_away="home",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-01"
        )

        key = build_context_key(ctx)

        self.assertIn("venue_id", key)
        self.assertIn("home_away", key)
        self.assertIn("coach_id_home", key)
        self.assertIn("coach_id_away", key)
        self.assertIn("game_date", key)
        self.assertEqual(key["venue_id"], "MSG")

    def test_build_context_key_excludes_game_id(self):
        """Verify game_id is not in context key."""
        ctx = GameContext(
            game_id="test_002",
            venue_id="ARENA",
            home_away="away",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-02"
        )

        key = build_context_key(ctx)

        self.assertNotIn("game_id", key)

    def test_hash_stability_across_runs(self):
        """Verify hash is deterministic."""
        key1 = {"venue_id": "MSG", "home_away": "home", "coach_id_home": "a"}
        key2 = {"venue_id": "MSG", "home_away": "home", "coach_id_home": "a"}

        hash1 = hash_key(key1)
        hash2 = hash_key(key2)

        self.assertEqual(hash1, hash2)

    def test_hash_different_for_different_keys(self):
        """Verify different contexts produce different hashes."""
        key1 = {"venue_id": "MSG", "home_away": "home"}
        key2 = {"venue_id": "STAPLES", "home_away": "home"}

        hash1 = hash_key(key1)
        hash2 = hash_key(key2)

        self.assertNotEqual(hash1, hash2)

    def test_hash_stable_with_reordered_keys(self):
        """Verify hash is stable regardless of dict order."""
        key1 = {"a": 1, "b": 2, "c": 3}
        key2 = {"c": 3, "a": 1, "b": 2}

        hash1 = hash_key(key1)
        hash2 = hash_key(key2)

        self.assertEqual(hash1, hash2)

    def test_hash_format(self):
        """Verify hash is SHA256 hex digest."""
        key = {"test": "value"}
        h = hash_key(key)

        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))


if __name__ == "__main__":
    unittest.main()
