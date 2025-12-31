"""
Keyed modifier selection and deterministic application.
"""
from typing import List
from .types import GameContext, MarketLine, Modifier


def select_modifiers(ctx: GameContext, catalog: List[Modifier]) -> List[Modifier]:
    """
    Select modifiers that match the current game context.

    A modifier is selected if its key_value matches the corresponding
    field in the GameContext.

    Args:
        ctx: GameContext instance
        catalog: Full list of available modifiers

    Returns:
        List of modifiers that apply to this context
    """
    selected = []

    # Build lookup map for context values
    context_values = {
        "venue_id": ctx.venue_id,
        "home_away": ctx.home_away,
        "coach_id_home": ctx.coach_id_home,
        "coach_id_away": ctx.coach_id_away,
    }

    # Add optional fields if present
    if ctx.days_rest_home is not None:
        context_values["days_rest_home"] = str(ctx.days_rest_home)
    if ctx.days_rest_away is not None:
        context_values["days_rest_away"] = str(ctx.days_rest_away)
    if ctx.travel_km_home is not None:
        context_values["travel_km_home"] = str(ctx.travel_km_home)
    if ctx.travel_km_away is not None:
        context_values["travel_km_away"] = str(ctx.travel_km_away)

    # Select modifiers where key matches context
    for mod in catalog:
        if mod.key in context_values and context_values[mod.key] == mod.key_value:
            selected.append(mod)

    return selected


def apply_modifiers(lines: List[MarketLine], mods: List[Modifier]) -> List[MarketLine]:
    """
    Apply modifiers to market lines with deterministic rounding.

    For each line, if any modifier applies to its stat_name,
    adjust the line by the modifier's weight (multiplicative).

    Args:
        lines: Original market lines
        mods: Modifiers to apply

    Returns:
        New list of MarketLine instances with adjusted values
    """
    adjusted = []

    for line in lines:
        # Start with original line value
        new_value = line.line

        # Apply all relevant modifiers
        for mod in mods:
            if line.stat_name in mod.applies_to:
                # Multiplicative adjustment: weight +0.03 => 1.03x
                new_value = new_value * (1.0 + mod.weight)

        # Round to 2 decimals for stability
        new_value = round(new_value, 2)

        # Create adjusted line
        adjusted.append(
            MarketLine(
                stat_name=line.stat_name,
                line=new_value,
                direction=line.direction
            )
        )

    return adjusted
