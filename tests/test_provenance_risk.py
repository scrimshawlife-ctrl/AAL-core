"""
Tests for risk provenance tracking.
"""
import unittest
from normalizers import load_preset
from risk import (
    LegSpec,
    recommend_limits,
    make_risk_provenance,
    RiskProvenanceRecord,
    ULTRA_SAFE,
)


class TestProvenanceRisk(unittest.TestCase):
    """Test risk provenance tracking."""

    def test_provenance_record_created(self):
        """Verify provenance record is created."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        provenance = make_risk_provenance(
            nba,
            ULTRA_SAFE,
            limits["entropy_score"],
            limits,
            legs
        )

        self.assertIsInstance(provenance, RiskProvenanceRecord)

    def test_provenance_includes_sport_id(self):
        """Verify provenance includes sport_id."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        provenance = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)

        self.assertEqual(provenance.sport_id, "NBA")

    def test_provenance_includes_mode(self):
        """Verify provenance includes mode."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        provenance = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)

        self.assertEqual(provenance.mode, ULTRA_SAFE)

    def test_provenance_includes_entropy_score(self):
        """Verify provenance includes entropy_score."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        provenance = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)

        self.assertGreater(provenance.entropy_score, 0.0)
        self.assertLess(provenance.entropy_score, 1.0)

    def test_provenance_hashes_are_stable(self):
        """Verify provenance hashes are stable across runs."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        prov1 = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)
        prov2 = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)

        # Hashes should be stable (timestamps will differ)
        self.assertEqual(prov1.normalizer_hash, prov2.normalizer_hash)
        self.assertEqual(prov1.throttle_hash, prov2.throttle_hash)
        self.assertEqual(prov1.inputs_hash, prov2.inputs_hash)

    def test_provenance_hash_format(self):
        """Verify hashes are SHA256 format."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        provenance = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)

        self.assertEqual(len(provenance.normalizer_hash), 64)
        self.assertEqual(len(provenance.throttle_hash), 64)
        self.assertEqual(len(provenance.inputs_hash), 64)

    def test_different_legs_different_hash(self):
        """Verify different legs produce different inputs_hash."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)

        legs1 = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]
        legs2 = [LegSpec("NBA", "assists", "BOS", "usage", 0.75)]

        prov1 = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs1)
        prov2 = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs2)

        self.assertNotEqual(prov1.inputs_hash, prov2.inputs_hash)

    def test_timestamp_format(self):
        """Verify timestamp is ISO format."""
        nba = load_preset("NBA")
        limits = recommend_limits(nba, ULTRA_SAFE)
        legs = [LegSpec("NBA", "points", "LAL", "usage", 0.80)]

        provenance = make_risk_provenance(nba, ULTRA_SAFE, limits["entropy_score"], limits, legs)

        # ISO format check (basic)
        self.assertIn("T", provenance.created_at_iso)


if __name__ == "__main__":
    unittest.main()
