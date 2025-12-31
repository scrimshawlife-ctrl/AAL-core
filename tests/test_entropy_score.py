"""
Tests for entropy scoring.
"""
import unittest
from normalizers import load_preset
from risk import entropy_score


class TestEntropyScore(unittest.TestCase):
    """Test entropy scoring from normalizers."""

    def test_nba_has_lowest_entropy(self):
        """Verify NBA has lowest entropy (most stable)."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")
        nfl = load_preset("NFL")

        nba_entropy, _ = entropy_score(nba)
        nhl_entropy, _ = entropy_score(nhl)
        nfl_entropy, _ = entropy_score(nfl)

        # NBA should have lowest entropy
        self.assertLess(nba_entropy, nhl_entropy)
        self.assertLess(nba_entropy, nfl_entropy)

    def test_nfl_has_highest_entropy(self):
        """Verify NFL has highest entropy (least stable)."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")
        nfl = load_preset("NFL")

        nba_entropy, _ = entropy_score(nba)
        nhl_entropy, _ = entropy_score(nhl)
        nfl_entropy, _ = entropy_score(nfl)

        # NFL should have highest entropy
        self.assertGreater(nfl_entropy, nba_entropy)
        self.assertGreater(nfl_entropy, nhl_entropy)

    def test_entropy_ordering_nba_nhl_nfl(self):
        """Verify entropy ordering: NBA < NHL < NFL."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")
        nfl = load_preset("NFL")

        nba_entropy, _ = entropy_score(nba)
        nhl_entropy, _ = entropy_score(nhl)
        nfl_entropy, _ = entropy_score(nfl)

        self.assertLess(nba_entropy, nhl_entropy)
        self.assertLess(nhl_entropy, nfl_entropy)

    def test_entropy_in_valid_range(self):
        """Verify entropy scores are in [0, 1]."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")
        nfl = load_preset("NFL")

        for cfg in [nba, nhl, nfl]:
            entropy, _ = entropy_score(cfg)
            self.assertGreaterEqual(entropy, 0.0)
            self.assertLessEqual(entropy, 1.0)

    def test_entropy_breakdown_included(self):
        """Verify breakdown dict is returned."""
        nba = load_preset("NBA")
        entropy, breakdown = entropy_score(nba)

        self.assertIn("base", breakdown)
        self.assertIn("shape_penalty", breakdown)
        self.assertIn("vol_penalty", breakdown)
        self.assertIn("total", breakdown)
        self.assertEqual(breakdown["total"], round(entropy, 4))

    def test_entropy_deterministic(self):
        """Verify entropy is deterministic across calls."""
        nba = load_preset("NBA")

        entropy1, _ = entropy_score(nba)
        entropy2, _ = entropy_score(nba)

        self.assertEqual(entropy1, entropy2)

    def test_breakdown_contains_components(self):
        """Verify breakdown contains individual components."""
        nba = load_preset("NBA")
        _, breakdown = entropy_score(nba)

        self.assertIn("stability", breakdown)
        self.assertIn("concentration", breakdown)
        self.assertIn("event_rate_norm", breakdown)
        self.assertIn("per_event_variance", breakdown)
        self.assertIn("game_level_variance", breakdown)


if __name__ == "__main__":
    unittest.main()
