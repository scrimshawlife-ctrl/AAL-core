"""
Tests for throttle recommendations.
"""
import unittest
from normalizers import load_preset
from risk import recommend_limits, ULTRA_SAFE, BALANCED, CORRELATED, LADDER


class TestThrottleRecommendations(unittest.TestCase):
    """Test throttle limit recommendations."""

    def test_nba_ultra_safe_max_legs(self):
        """Verify NBA ultra_safe allows 5 legs."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)

        self.assertEqual(limits["max_legs"], 5)

    def test_nfl_ultra_safe_max_legs(self):
        """Verify NFL ultra_safe allows 2-3 legs (lower due to very high entropy)."""
        nfl = load_preset("NFL")
        limits = recommend_limits(nfl, ULTRA_SAFE)

        # NFL has very high entropy (>0.75), gets 2 legs
        self.assertIn(limits["max_legs"], [2, 3])

    def test_nba_allows_more_legs_than_nfl(self):
        """Verify NBA allows more legs than NFL in same mode."""
        nba = load_preset("NBA")
        nfl = load_preset("NFL")

        nba_limits = recommend_limits(nba, BALANCED)
        nfl_limits = recommend_limits(nfl, BALANCED)

        self.assertGreater(nba_limits["max_legs"], nfl_limits["max_legs"])

    def test_ultra_safe_min_survivability(self):
        """Verify ultra_safe has 0.70 min survivability."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)

        self.assertEqual(limits["min_survivability"], 0.70)

    def test_balanced_min_survivability(self):
        """Verify balanced has 0.60 min survivability."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, BALANCED)

        self.assertEqual(limits["min_survivability"], 0.60)

    def test_ultra_safe_disallows_event_primitives(self):
        """Verify ultra_safe never allows event primitives."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")
        nfl = load_preset("NFL")

        for cfg in [nba, nhl, nfl]:
            limits = recommend_limits(cfg, ULTRA_SAFE)
            self.assertFalse(limits["allow_event_primitives"])

    def test_balanced_allows_events_for_low_entropy(self):
        """Verify balanced allows event primitives for low entropy sports."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, BALANCED)

        # NBA has low entropy, should allow events in balanced
        self.assertTrue(limits["allow_event_primitives"])

    def test_entropy_score_included(self):
        """Verify entropy_score is included in limits."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)

        self.assertIn("entropy_score", limits)
        self.assertGreater(limits["entropy_score"], 0.0)

    def test_notes_included(self):
        """Verify notes are included."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)

        self.assertIn("notes", limits)
        self.assertIsInstance(limits["notes"], str)
        self.assertGreater(len(limits["notes"]), 0)

    def test_invalid_mode_raises(self):
        """Verify invalid mode raises ValueError."""
        nba = load_preset("NBA")

        with self.assertRaises(ValueError) as ctx:
            recommend_limits(nba, "invalid_mode")

        self.assertIn("Invalid mode", str(ctx.exception))

    def test_all_modes_valid(self):
        """Verify all standard modes are accepted."""
        nba = load_preset("NBA")

        for mode in [ULTRA_SAFE, BALANCED, CORRELATED, LADDER]:
            limits = recommend_limits(nba, mode)
            self.assertIsInstance(limits, dict)

    def test_max_same_team_legs_varies_by_entropy(self):
        """Verify max_same_team_legs varies by sport entropy."""
        nba = load_preset("NBA")
        nfl = load_preset("NFL")

        nba_limits = recommend_limits(nba, ULTRA_SAFE)
        nfl_limits = recommend_limits(nfl, ULTRA_SAFE)

        # NBA (low entropy) allows more same-team legs
        self.assertGreaterEqual(
            nba_limits["max_same_team_legs"],
            nfl_limits["max_same_team_legs"]
        )


if __name__ == "__main__":
    unittest.main()
