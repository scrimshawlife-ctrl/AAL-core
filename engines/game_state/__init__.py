"""
GameState engine for deterministic, leakage-free game execution.

This module enforces:
- Hard reset per game (no cross-game contamination)
- Keyed context modifiers (venue, coach, rest/travel)
- Backtest validation harness
- Leakage detection guards
- Full provenance audit trails

Integration example for HollerSports:

    from aal_core.engines.game_state.reset import new_game_state
    from aal_core.engines.game_state.modifiers import select_modifiers, apply_modifiers
    from aal_core.engines.game_state.provenance import make_provenance
    from aal_core.engines.game_state.guards import assert_no_leakage

    # Create cold-start state
    state = new_game_state(game_id, context)

    # Verify no leakage
    assert_no_leakage(state, game_id)

    # Apply modifiers
    selected = select_modifiers(context, modifier_catalog)
    adjusted_lines = apply_modifiers(base_lines, selected)

    # Generate provenance
    provenance = make_provenance(state, context, base_lines, selected)
"""

from .types import (
    GameContext,
    MarketLine,
    Modifier,
    GameState,
    ProvenanceRecord,
    RunResult,
)
from .context_keys import build_context_key, hash_key
from .reset import new_game_state
from .modifiers import select_modifiers, apply_modifiers
from .guards import assert_no_leakage, FORBIDDEN_STATE_KEYS
from .provenance import fingerprint_inputs, make_provenance
from .backtest import evaluate_mae, backtest_modifier_effect

__all__ = [
    # Types
    "GameContext",
    "MarketLine",
    "Modifier",
    "GameState",
    "ProvenanceRecord",
    "RunResult",
    # Context keys
    "build_context_key",
    "hash_key",
    # Reset
    "new_game_state",
    # Modifiers
    "select_modifiers",
    "apply_modifiers",
    # Guards
    "assert_no_leakage",
    "FORBIDDEN_STATE_KEYS",
    # Provenance
    "fingerprint_inputs",
    "make_provenance",
    # Backtest
    "evaluate_mae",
    "backtest_modifier_effect",
]
