"""
Backtesting harness for rolling-window validation of modifiers.
"""
from typing import List, Dict, Any, Callable


def evaluate_mae(preds: List[float], actuals: List[float]) -> float:
    """
    Compute Mean Absolute Error between predictions and actuals.

    Args:
        preds: Predicted values
        actuals: Actual values

    Returns:
        MAE (mean absolute error)

    Raises:
        ValueError: If lists have different lengths or are empty
    """
    if len(preds) != len(actuals):
        raise ValueError(f"Length mismatch: {len(preds)} predictions vs {len(actuals)} actuals")

    if len(preds) == 0:
        raise ValueError("Cannot compute MAE on empty lists")

    errors = [abs(pred - actual) for pred, actual in zip(preds, actuals)]
    return sum(errors) / len(errors)


def backtest_modifier_effect(
    rows: List[Dict[str, Any]],
    base_predict_fn: Callable[[Dict[str, Any]], float],
    modifier_apply_fn: Callable[[Dict[str, Any]], float]
) -> Dict[str, Any]:
    """
    Evaluate the impact of modifiers on prediction accuracy.

    Args:
        rows: List of game records, each containing:
            - "ctx": GameContext or dict
            - "base_lines": list of MarketLine or dicts
            - "actuals": list of actual outcomes
        base_predict_fn: Function that takes a row and returns base prediction
        modifier_apply_fn: Function that takes a row and returns modified prediction

    Returns:
        Dictionary with:
            - "mae_before": MAE without modifiers
            - "mae_after": MAE with modifiers
            - "delta": Improvement (negative = better)
            - "n": Number of games evaluated
    """
    if not rows:
        return {
            "mae_before": 0.0,
            "mae_after": 0.0,
            "delta": 0.0,
            "n": 0
        }

    base_preds = []
    modified_preds = []
    actuals = []

    for row in rows:
        # Get predictions
        base_pred = base_predict_fn(row)
        modified_pred = modifier_apply_fn(row)

        # Get actual outcome (support both single value and list)
        actual = row.get("actual") or row.get("actuals")
        if isinstance(actual, list):
            actual = actual[0] if actual else 0.0

        base_preds.append(base_pred)
        modified_preds.append(modified_pred)
        actuals.append(float(actual))

    # Compute MAE for both approaches
    mae_before = evaluate_mae(base_preds, actuals)
    mae_after = evaluate_mae(modified_preds, actuals)
    delta = mae_after - mae_before

    return {
        "mae_before": round(mae_before, 4),
        "mae_after": round(mae_after, 4),
        "delta": round(delta, 4),
        "n": len(rows)
    }
