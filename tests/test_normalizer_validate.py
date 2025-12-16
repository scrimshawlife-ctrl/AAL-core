"""
Tests for normalizer validation logic.
"""
import unittest
from normalizers import (
    load_preset,
    validate_normalizer,
    SportNormalizerConfig,
    OpportunitySpec,
    UsageSpec,
    ContinuitySpec,
    VolatilitySpec,
    FailureModes,
    FailureEffects,
    StatSpec,
    Primitive,
    DistributionShape,
)


class TestNormalizerValidate(unittest.TestCase):
    """Test normalizer validation."""

    def test_validate_nba_passes(self):
        """Verify NBA preset passes validation."""
        config = load_preset("NBA")

        # Should not raise
        validate_normalizer(config)

    def test_validate_nhl_passes(self):
        """Verify NHL preset passes validation."""
        config = load_preset("NHL")

        # Should not raise
        validate_normalizer(config)

    def test_validate_nfl_passes(self):
        """Verify NFL preset passes validation."""
        config = load_preset("NFL")

        # Should not raise
        validate_normalizer(config)

    def test_invalid_stability_score_raises(self):
        """Verify out-of-range stability_score raises error."""
        with self.assertRaises(ValueError) as ctx:
            OpportunitySpec(unit="minutes", stability_score=1.5)

        self.assertIn("stability_score", str(ctx.exception))

    def test_negative_stability_score_raises(self):
        """Verify negative stability_score raises error."""
        with self.assertRaises(ValueError) as ctx:
            OpportunitySpec(unit="minutes", stability_score=-0.1)

        self.assertIn("stability_score", str(ctx.exception))

    def test_invalid_concentration_score_raises(self):
        """Verify out-of-range concentration_score raises error."""
        with self.assertRaises(ValueError) as ctx:
            UsageSpec(unit="usage_rate", concentration_score=2.0)

        self.assertIn("concentration_score", str(ctx.exception))

    def test_negative_event_rate_raises(self):
        """Verify negative event_rate raises error."""
        with self.assertRaises(ValueError) as ctx:
            ContinuitySpec(
                event_rate=-10.0,
                distribution_shape=DistributionShape.NORMAL
            )

        self.assertIn("event_rate", str(ctx.exception))

    def test_negative_per_event_variance_raises(self):
        """Verify negative per_event_variance raises error."""
        with self.assertRaises(ValueError) as ctx:
            VolatilitySpec(per_event_variance=-0.1, game_level_variance=0.2)

        self.assertIn("per_event_variance", str(ctx.exception))

    def test_negative_game_level_variance_raises(self):
        """Verify negative game_level_variance raises error."""
        with self.assertRaises(ValueError) as ctx:
            VolatilitySpec(per_event_variance=0.1, game_level_variance=-0.2)

        self.assertIn("game_level_variance", str(ctx.exception))

    def test_invalid_survivability_score_raises(self):
        """Verify out-of-range survivability_score raises error."""
        with self.assertRaises(ValueError) as ctx:
            StatSpec(primitive=Primitive.USAGE, survivability_score=1.1)

        self.assertIn("survivability_score", str(ctx.exception))

    def test_empty_stat_map_raises(self):
        """Verify empty stat_map raises error."""
        with self.assertRaises(ValueError):
            SportNormalizerConfig(
                schema_version="1.0",
                sport_id="TEST",
                version="1.0",
                opportunity=OpportunitySpec("minutes", 0.8),
                usage=UsageSpec("usage_rate", 0.7),
                continuity=ContinuitySpec(95, DistributionShape.NORMAL),
                volatility=VolatilitySpec(0.1, 0.2),
                failure_modes=FailureModes(
                    "test",
                    FailureEffects([], [])
                ),
                stat_map={},  # Empty
            )

    def test_invalid_schema_version_raises(self):
        """Verify invalid schema_version raises error."""
        with self.assertRaises(ValueError) as ctx:
            SportNormalizerConfig(
                schema_version="2.0",  # Invalid
                sport_id="TEST",
                version="1.0",
                opportunity=OpportunitySpec("minutes", 0.8),
                usage=UsageSpec("usage_rate", 0.7),
                continuity=ContinuitySpec(95, DistributionShape.NORMAL),
                volatility=VolatilitySpec(0.1, 0.2),
                failure_modes=FailureModes(
                    "test",
                    FailureEffects([], [])
                ),
                stat_map={"test": StatSpec(Primitive.USAGE, 0.5)},
            )

        self.assertIn("schema_version", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
