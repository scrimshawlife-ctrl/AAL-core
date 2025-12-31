"""
Tests for backtest evaluation harness.
"""
import unittest
from engines.game_state.backtest import evaluate_mae, backtest_modifier_effect


class TestBacktestSmoke(unittest.TestCase):
    """Smoke tests for backtest functionality."""

    def test_evaluate_mae_simple(self):
        """Verify MAE calculation."""
        preds = [10.0, 20.0, 30.0]
        actuals = [12.0, 19.0, 28.0]

        mae = evaluate_mae(preds, actuals)

        # |10-12| + |20-19| + |30-28| = 2 + 1 + 2 = 5 / 3 = 1.666...
        self.assertAlmostEqual(mae, 1.6667, places=4)

    def test_evaluate_mae_perfect_predictions(self):
        """Verify MAE is 0 for perfect predictions."""
        preds = [5.0, 10.0, 15.0]
        actuals = [5.0, 10.0, 15.0]

        mae = evaluate_mae(preds, actuals)

        self.assertEqual(mae, 0.0)

    def test_evaluate_mae_length_mismatch_raises(self):
        """Verify length mismatch raises error."""
        preds = [1.0, 2.0]
        actuals = [1.0, 2.0, 3.0]

        with self.assertRaises(ValueError) as ctx:
            evaluate_mae(preds, actuals)

        self.assertIn("Length mismatch", str(ctx.exception))

    def test_evaluate_mae_empty_lists_raises(self):
        """Verify empty lists raise error."""
        preds = []
        actuals = []

        with self.assertRaises(ValueError) as ctx:
            evaluate_mae(preds, actuals)

        self.assertIn("empty", str(ctx.exception))

    def test_backtest_modifier_effect_simple(self):
        """Verify backtest returns structured output."""
        rows = [
            {"base": 10.0, "modified": 10.5, "actual": 11.0},
            {"base": 20.0, "modified": 20.5, "actual": 21.0},
        ]

        def base_fn(row):
            return row["base"]

        def mod_fn(row):
            return row["modified"]

        result = backtest_modifier_effect(rows, base_fn, mod_fn)

        self.assertIn("mae_before", result)
        self.assertIn("mae_after", result)
        self.assertIn("delta", result)
        self.assertIn("n", result)
        self.assertEqual(result["n"], 2)

    def test_backtest_modifier_effect_improvement(self):
        """Verify backtest detects improvement."""
        rows = [
            {"base": 10.0, "modified": 11.0, "actual": 11.0},
            {"base": 20.0, "modified": 21.0, "actual": 21.0},
        ]

        def base_fn(row):
            return row["base"]

        def mod_fn(row):
            return row["modified"]

        result = backtest_modifier_effect(rows, base_fn, mod_fn)

        # Base MAE: (|10-11| + |20-21|) / 2 = 1.0
        # Modified MAE: (|11-11| + |21-21|) / 2 = 0.0
        # Delta: 0.0 - 1.0 = -1.0 (improvement)
        self.assertAlmostEqual(result["mae_before"], 1.0, places=4)
        self.assertAlmostEqual(result["mae_after"], 0.0, places=4)
        self.assertAlmostEqual(result["delta"], -1.0, places=4)

    def test_backtest_modifier_effect_empty_rows(self):
        """Verify empty rows returns zero values."""
        rows = []

        def base_fn(row):
            return 0.0

        def mod_fn(row):
            return 0.0

        result = backtest_modifier_effect(rows, base_fn, mod_fn)

        self.assertEqual(result["mae_before"], 0.0)
        self.assertEqual(result["mae_after"], 0.0)
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(result["n"], 0)

    def test_backtest_modifier_effect_handles_list_actual(self):
        """Verify backtest handles actual as list."""
        rows = [
            {"base": 10.0, "modified": 10.5, "actuals": [11.0]},
        ]

        def base_fn(row):
            return row["base"]

        def mod_fn(row):
            return row["modified"]

        result = backtest_modifier_effect(rows, base_fn, mod_fn)

        self.assertEqual(result["n"], 1)
        self.assertIsInstance(result["mae_before"], float)


if __name__ == "__main__":
    unittest.main()
