"""
Tests for preset normalizer integrity.
"""
import unittest
from normalizers import (
    load_preset,
    validate_normalizer,
    make_provenance,
    ProvenanceRecord,
    DistributionShape,
    Primitive,
)


class TestPresetIntegrity(unittest.TestCase):
    """Test preset normalizer integrity."""

    def test_nba_loads_and_validates(self):
        """Verify NBA preset loads and validates."""
        config = load_preset("NBA")

        # Should not raise
        validate_normalizer(config)

        self.assertEqual(config.sport_id, "NBA")
        self.assertEqual(config.schema_version, "1.0")

    def test_nhl_loads_and_validates(self):
        """Verify NHL preset loads and validates."""
        config = load_preset("NHL")

        # Should not raise
        validate_normalizer(config)

        self.assertEqual(config.sport_id, "NHL")

    def test_nfl_loads_and_validates(self):
        """Verify NFL preset loads and validates."""
        config = load_preset("NFL")

        # Should not raise
        validate_normalizer(config)

        self.assertEqual(config.sport_id, "NFL")

    def test_nba_provenance_includes_hash(self):
        """Verify provenance record includes config hash."""
        config = load_preset("NBA")
        provenance = make_provenance(config)

        self.assertIsInstance(provenance, ProvenanceRecord)
        self.assertEqual(len(provenance.config_hash), 64)
        self.assertEqual(provenance.sport_id, "NBA")
        self.assertEqual(provenance.schema_version, "1.0")

    def test_nba_distribution_shape(self):
        """Verify NBA has normal distribution."""
        config = load_preset("NBA")

        self.assertEqual(config.continuity.distribution_shape, DistributionShape.NORMAL)

    def test_nhl_distribution_shape(self):
        """Verify NHL has skewed distribution."""
        config = load_preset("NHL")

        self.assertEqual(config.continuity.distribution_shape, DistributionShape.SKEWED)

    def test_nfl_distribution_shape(self):
        """Verify NFL has spiky distribution."""
        config = load_preset("NFL")

        self.assertEqual(config.continuity.distribution_shape, DistributionShape.SPIKY)

    def test_nba_stat_primitives(self):
        """Verify NBA stat primitives are correct."""
        config = load_preset("NBA")

        self.assertEqual(config.stat_map["points"].primitive, Primitive.USAGE)
        self.assertEqual(config.stat_map["assists"].primitive, Primitive.USAGE)
        self.assertEqual(config.stat_map["rebounds"].primitive, Primitive.OPPORTUNITY)
        self.assertEqual(config.stat_map["PRA"].primitive, Primitive.HYBRID)

    def test_nba_failure_modes_definition(self):
        """Verify NBA failure modes are defined."""
        config = load_preset("NBA")

        self.assertIn("trailing", config.failure_modes.bad_script_definition.lower())
        self.assertIn("points", config.failure_modes.bad_script_effects.suppresses)
        self.assertIn("assists", config.failure_modes.bad_script_effects.inflates)

    def test_nba_stability_in_range(self):
        """Verify NBA stability score is in valid range."""
        config = load_preset("NBA")

        self.assertGreaterEqual(config.opportunity.stability_score, 0.0)
        self.assertLessEqual(config.opportunity.stability_score, 1.0)

    def test_all_presets_have_unique_hashes(self):
        """Verify each preset has unique hash."""
        nba = load_preset("NBA")
        nhl = load_preset("NHL")
        nfl = load_preset("NFL")

        nba_prov = make_provenance(nba)
        nhl_prov = make_provenance(nhl)
        nfl_prov = make_provenance(nfl)

        hashes = {nba_prov.config_hash, nhl_prov.config_hash, nfl_prov.config_hash}
        self.assertEqual(len(hashes), 3)

    def test_provenance_timestamp_format(self):
        """Verify provenance timestamp is ISO format."""
        config = load_preset("NBA")
        provenance = make_provenance(config)

        # ISO format check (basic)
        self.assertIn("T", provenance.created_at_iso)

    def test_nba_event_rate(self):
        """Verify NBA event rate is 95."""
        config = load_preset("NBA")

        self.assertEqual(config.continuity.event_rate, 95)

    def test_nhl_event_rate(self):
        """Verify NHL event rate is 55."""
        config = load_preset("NHL")

        self.assertEqual(config.continuity.event_rate, 55)

    def test_nfl_event_rate(self):
        """Verify NFL event rate is 60."""
        config = load_preset("NFL")

        self.assertEqual(config.continuity.event_rate, 60)


if __name__ == "__main__":
    unittest.main()
