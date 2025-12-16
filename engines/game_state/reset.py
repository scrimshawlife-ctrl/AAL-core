"""
Hard reset enforcement for game state initialization.
Ensures no cross-game leakage via cold-start policy.
"""
from datetime import datetime
from .types import GameState, GameContext
from .context_keys import build_context_key, hash_key


def new_game_state(game_id: str, ctx: GameContext) -> GameState:
    """
    Create a fresh GameState with mandatory cold start.

    Every game must start with:
    - Empty internal_state dict
    - No applied_modifiers
    - Fresh context key hash
    - Current timestamp

    Args:
        game_id: Unique identifier for this game
        ctx: GameContext with venue, coaches, rest/travel, etc.

    Returns:
        GameState initialized for cold start
    """
    # Build and hash the context key
    context_dict = build_context_key(ctx)
    context_hash = hash_key(context_dict)

    # Create state with enforced empty initialization
    state = GameState(
        game_id=game_id,
        created_at=datetime.utcnow().isoformat(),
        context_key=context_hash,
        applied_modifiers=[],
        internal_state={}  # MANDATORY: no carryover state
    )

    return state
