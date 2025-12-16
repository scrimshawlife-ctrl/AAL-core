"""
Demonstration of the game state system with Knicks vs Spurs example.
Shows cold start, modifier selection, application, and provenance.
"""
from .types import GameContext, MarketLine, Modifier, RunResult
from .reset import new_game_state
from .modifiers import select_modifiers, apply_modifiers
from .provenance import make_provenance
from .guards import assert_no_leakage


# Define a small modifier catalog for demonstration
CATALOG = [
    # Venue modifier: MSG boosts guard usage
    Modifier(
        name="msg_guard_boost",
        key="venue_id",
        key_value="MSG",
        applies_to=["points", "assists"],
        weight=0.03,
        notes="Madison Square Garden typically sees higher guard usage"
    ),
    # Coach modifier: Thibs increases minutes stability
    Modifier(
        name="thibs_stability",
        key="coach_id_home",
        key_value="coach_thibs",
        applies_to=["points", "rebounds", "assists"],
        weight=0.02,
        notes="Thibodeau's system increases player consistency"
    ),
    # Opponent modifier: Spurs variance reduction
    Modifier(
        name="spurs_variance_reduction",
        key="coach_id_away",
        key_value="coach_pop",
        applies_to=["rebounds"],
        weight=-0.01,
        notes="Popovich's defensive scheme reduces rebounding variance"
    ),
]


def run_example() -> RunResult:
    """
    Execute a complete game state workflow.

    Returns:
        RunResult with state, provenance, and adjusted lines
    """
    # Define game context (Knicks home vs Spurs)
    ctx = GameContext(
        game_id="nyk_sas_20250115",
        venue_id="MSG",
        home_away="home",
        coach_id_home="coach_thibs",
        coach_id_away="coach_pop",
        game_date="2025-01-15",
        days_rest_home=2,
        days_rest_away=1,
        travel_km_home=0.0,
        travel_km_away=2800.0
    )

    # Create cold-start state
    state = new_game_state(ctx.game_id, ctx)

    # Verify no leakage
    assert_no_leakage(state, ctx.game_id)

    # Define base market lines (example player props)
    base_lines = [
        MarketLine(stat_name="points", line=24.5, direction="over"),
        MarketLine(stat_name="assists", line=6.5, direction="over"),
        MarketLine(stat_name="rebounds", line=8.0, direction="over"),
    ]

    # Select applicable modifiers
    selected_mods = select_modifiers(ctx, CATALOG)

    # Apply modifiers to lines
    adjusted_lines = apply_modifiers(base_lines, selected_mods)

    # Update state with applied modifiers
    state.applied_modifiers = [mod.name for mod in selected_mods]

    # Generate provenance
    provenance = make_provenance(state, ctx, base_lines, selected_mods)

    # Return complete result
    return RunResult(
        state=state,
        provenance=provenance,
        adjusted_lines=adjusted_lines
    )


def main():
    """Run the example and print results."""
    print("=" * 60)
    print("Game State System: Example Execution")
    print("=" * 60)

    result = run_example()

    print("\n[1] Game State")
    print(f"  Game ID: {result.state.game_id}")
    print(f"  Context Key: {result.state.context_key[:16]}...")
    print(f"  Applied Modifiers: {result.state.applied_modifiers}")
    print(f"  Internal State: {result.state.internal_state}")

    print("\n[2] Provenance")
    print(f"  Timestamp: {result.provenance.timestamp_iso}")
    print(f"  Context Hash: {result.provenance.context_key_hash[:16]}...")
    print(f"  Modifier Set Hash: {result.provenance.modifier_set_hash[:16]}...")
    print(f"  Inputs Fingerprint: {result.provenance.inputs_fingerprint[:16]}...")
    print(f"  Code Version: {result.provenance.code_version}")

    print("\n[3] Adjusted Lines")
    for line in result.adjusted_lines:
        print(f"  {line.stat_name}: {line.line} ({line.direction})")

    print("\n" + "=" * 60)
    print("Execution complete. All guards passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
