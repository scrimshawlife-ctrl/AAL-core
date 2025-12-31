"""
Tests for policy enforcement.
"""
import unittest
from normalizers import load_preset
from risk import LegSpec, enforce_policy, ULTRA_SAFE, BALANCED


class TestPolicyEnforcement(unittest.TestCase):
    """Test policy enforcement logic."""

    def test_event_primitive_rejected_in_ultra_safe(self):
        """Verify event primitives are rejected in ultra_safe."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "points", "LAL", "usage", 0.80),
            LegSpec("NBA", "touchdowns", "LAL", "event", 0.30),  # Event primitive
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        self.assertFalse(result["ok"])
        self.assertIn(1, result["dropped_indices"])  # Index 1 is event
        self.assertEqual(result["failed_count"], 1)

    def test_low_survivability_dropped_in_ultra_safe(self):
        """Verify low survivability legs are dropped in ultra_safe."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "points", "LAL", "usage", 0.80),
            LegSpec("NBA", "assists", "LAL", "usage", 0.50),  # Below 0.70 threshold
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        self.assertFalse(result["ok"])
        self.assertIn(1, result["dropped_indices"])

    def test_same_team_overage_dropped_deterministically(self):
        """Verify excess same-team legs are dropped by lowest survivability."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "points", "LAL", "usage", 0.80),
            LegSpec("NBA", "assists", "LAL", "usage", 0.75),
            LegSpec("NBA", "rebounds", "LAL", "opportunity", 0.70),  # 3rd from LAL
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        # Ultra-safe allows max 2 same-team for NBA (low entropy)
        # Should drop index 2 (lowest survivability among LAL legs)
        self.assertFalse(result["ok"])
        self.assertIn(2, result["dropped_indices"])

    def test_total_leg_count_enforced(self):
        """Verify total leg count is enforced."""
        nba = load_preset("NBA")

        # Create 10 legs (exceeds ultra_safe max of 5)
        legs = [
            LegSpec("NBA", f"stat_{i}", f"TEAM_{i}", "usage", 0.75)
            for i in range(10)
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        self.assertFalse(result["ok"])
        self.assertEqual(result["passed_count"], 5)
        self.assertEqual(result["failed_count"], 5)

    def test_clean_legs_pass(self):
        """Verify valid legs pass policy."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "points", "LAL", "usage", 0.80),
            LegSpec("NBA", "assists", "BOS", "usage", 0.75),
            LegSpec("NBA", "rebounds", "GSW", "opportunity", 0.78),
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["dropped_indices"]), 0)
        self.assertEqual(result["passed_count"], 3)

    def test_dropped_indices_sorted(self):
        """Verify dropped_indices are sorted."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "stat1", "LAL", "usage", 0.80),
            LegSpec("NBA", "stat2", "LAL", "usage", 0.75),
            LegSpec("NBA", "stat3", "LAL", "usage", 0.70),  # 3 from same team
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        # Indices should be sorted
        self.assertEqual(result["dropped_indices"], sorted(result["dropped_indices"]))

    def test_reasons_provided(self):
        """Verify reasons are provided for failures."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "touchdowns", "LAL", "event", 0.30),
        ]

        result = enforce_policy(nba, ULTRA_SAFE, legs)

        self.assertFalse(result["ok"])
        self.assertGreater(len(result["reasons"]), 0)
        self.assertIsInstance(result["reasons"][0], str)

    def test_balanced_allows_one_high_variance_leg(self):
        """Verify balanced mode allows 1 high variance leg."""
        nba = load_preset("NBA")

        legs = [
            LegSpec("NBA", "points", "LAL", "usage", 0.80),
            LegSpec("NBA", "assists", "BOS", "usage", 0.55),  # Below 0.60 threshold
        ]

        result = enforce_policy(nba, BALANCED, legs)

        # Balanced allows 1 high variance leg
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
