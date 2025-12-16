"""
Tests for normalizer loading functionality.
"""
import unittest
from normalizers import load_preset, SportNormalizerConfig


class TestNormalizerLoad(unittest.TestCase):
    """Test normalizer loading."""

    def test_load_preset_nba(self):
        """Verify NBA preset loads successfully."""
        config = load_preset("NBA")

        self.assertIsInstance(config, SportNormalizerConfig)
        self.assertEqual(config.sport_id, "NBA")
        self.assertEqual(config.schema_version, "1.0")
        self.assertEqual(config.version, "1.0")

    def test_load_preset_nhl(self):
        """Verify NHL preset loads successfully."""
        config = load_preset("NHL")

        self.assertIsInstance(config, SportNormalizerConfig)
        self.assertEqual(config.sport_id, "NHL")

    def test_load_preset_nfl(self):
        """Verify NFL preset loads successfully."""
        config = load_preset("NFL")

        self.assertIsInstance(config, SportNormalizerConfig)
        self.assertEqual(config.sport_id, "NFL")

    def test_load_preset_case_insensitive(self):
        """Verify preset loading is case-insensitive."""
        config_upper = load_preset("NBA")
        config_lower = load_preset("nba")

        self.assertEqual(config_upper.sport_id, config_lower.sport_id)

    def test_load_preset_invalid_raises(self):
        """Verify invalid preset raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_preset("INVALID_SPORT")

    def test_nba_opportunity_unit(self):
        """Verify NBA opportunity unit is 'minutes'."""
        config = load_preset("NBA")

        self.assertEqual(config.opportunity.unit, "minutes")

    def test_nba_usage_unit(self):
        """Verify NBA usage unit is 'usage_rate'."""
        config = load_preset("NBA")

        self.assertEqual(config.usage.unit, "usage_rate")

    def test_nba_has_stat_map(self):
        """Verify NBA has non-empty stat_map."""
        config = load_preset("NBA")

        self.assertGreater(len(config.stat_map), 0)
        self.assertIn("points", config.stat_map)

    def test_loaded_config_has_metadata(self):
        """Verify loaded configs include optional metadata."""
        config = load_preset("NBA")

        self.assertIsNotNone(config.meta)
        self.assertIn("notes", config.meta)


if __name__ == "__main__":
    unittest.main()
