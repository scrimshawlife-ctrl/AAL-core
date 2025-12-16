"""
Tests for modifier selection and application.
"""
import unittest
from engines.game_state.types import GameContext, MarketLine, Modifier
from engines.game_state.modifiers import select_modifiers, apply_modifiers


class TestModifierApply(unittest.TestCase):
    """Test modifier selection and application logic."""

    def test_select_modifiers_by_venue(self):
        """Verify venue-based modifier selection."""
        ctx = GameContext(
            game_id="test_001",
            venue_id="MSG",
            home_away="home",
            coach_id_home="coach_a",
            coach_id_away="coach_b",
            game_date="2025-01-01"
        )

        catalog = [
            Modifier("mod1", "venue_id", "MSG", ["points"], 0.03),
            Modifier("mod2", "venue_id", "STAPLES", ["points"], 0.02),
        ]

        selected = select_modifiers(ctx, catalog)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].name, "mod1")

    def test_select_modifiers_by_coach(self):
        """Verify coach-based modifier selection."""
        ctx = GameContext(
            game_id="test_002",
            venue_id="ARENA",
            home_away="home",
            coach_id_home="coach_thibs",
            coach_id_away="coach_pop",
            game_date="2025-01-02"
        )

        catalog = [
            Modifier("thibs_mod", "coach_id_home", "coach_thibs", ["rebounds"], 0.02),
            Modifier("pop_mod", "coach_id_away", "coach_pop", ["assists"], -0.01),
            Modifier("other_mod", "coach_id_home", "coach_other", ["points"], 0.01),
        ]

        selected = select_modifiers(ctx, catalog)

        self.assertEqual(len(selected), 2)
        names = [m.name for m in selected]
        self.assertIn("thibs_mod", names)
        self.assertIn("pop_mod", names)

    def test_apply_modifiers_positive_weight(self):
        """Verify positive weight application."""
        lines = [MarketLine("points", 20.0, "over")]
        mods = [Modifier("boost", "venue_id", "MSG", ["points"], 0.03)]

        adjusted = apply_modifiers(lines, mods)

        # 20.0 * 1.03 = 20.60
        self.assertEqual(adjusted[0].line, 20.60)

    def test_apply_modifiers_negative_weight(self):
        """Verify negative weight application."""
        lines = [MarketLine("rebounds", 10.0, "over")]
        mods = [Modifier("reduce", "coach_id_away", "coach_x", ["rebounds"], -0.02)]

        adjusted = apply_modifiers(lines, mods)

        # 10.0 * 0.98 = 9.80
        self.assertEqual(adjusted[0].line, 9.80)

    def test_apply_modifiers_rounding(self):
        """Verify deterministic rounding to 2 decimals."""
        lines = [MarketLine("assists", 7.0, "over")]
        mods = [Modifier("mod", "venue_id", "V", ["assists"], 0.0123)]

        adjusted = apply_modifiers(lines, mods)

        # 7.0 * 1.0123 = 7.0861 -> rounds to 7.09
        self.assertEqual(adjusted[0].line, 7.09)

    def test_apply_modifiers_multiple_on_same_stat(self):
        """Verify multiple modifiers stack multiplicatively."""
        lines = [MarketLine("points", 25.0, "over")]
        mods = [
            Modifier("mod1", "venue_id", "V", ["points"], 0.03),
            Modifier("mod2", "coach_id_home", "C", ["points"], 0.02),
        ]

        adjusted = apply_modifiers(lines, mods)

        # 25.0 * 1.03 * 1.02 = 26.265 -> rounds to 26.27 or 26.26
        self.assertAlmostEqual(adjusted[0].line, 26.27, places=2)

    def test_apply_modifiers_no_effect_if_stat_not_matched(self):
        """Verify modifiers don't affect unrelated stats."""
        lines = [MarketLine("rebounds", 8.0, "over")]
        mods = [Modifier("mod", "venue_id", "V", ["points", "assists"], 0.05)]

        adjusted = apply_modifiers(lines, mods)

        self.assertEqual(adjusted[0].line, 8.0)

    def test_apply_modifiers_preserves_direction(self):
        """Verify direction field is preserved."""
        lines = [MarketLine("points", 22.5, "under")]
        mods = [Modifier("mod", "venue_id", "V", ["points"], 0.01)]

        adjusted = apply_modifiers(lines, mods)

        self.assertEqual(adjusted[0].direction, "under")

    def test_empty_modifier_list(self):
        """Verify empty modifier list returns unchanged lines."""
        lines = [MarketLine("points", 20.0, "over")]
        mods = []

        adjusted = apply_modifiers(lines, mods)

        self.assertEqual(adjusted[0].line, 20.0)


if __name__ == "__main__":
    unittest.main()
