"""
Leakage detection guards to prevent cross-game contamination.
"""
from .types import GameState


# Forbidden keys that indicate cross-game leakage
FORBIDDEN_STATE_KEYS = {
    "prior_game_tempo",
    "prior_volatility",
    "last_opponent_profile",
    "carryover",
    "last_game_id",
    "previous_outcome",
    "historical_variance",
    "accumulated_stats",
}


def assert_no_leakage(state: GameState, game_id: str) -> None:
    """
    Verify that GameState contains no cross-game contamination.

    Checks:
    1. state.game_id matches the expected game_id
    2. internal_state contains no forbidden keys

    Args:
        state: GameState to validate
        game_id: Expected game_id

    Raises:
        ValueError: If leakage is detected
    """
    # Check game_id match
    if state.game_id != game_id:
        raise ValueError(
            f"Leakage detected: state.game_id '{state.game_id}' "
            f"does not match expected '{game_id}'"
        )

    # Check for forbidden state keys
    state_keys = set(state.internal_state.keys())
    forbidden_found = state_keys & FORBIDDEN_STATE_KEYS

    if forbidden_found:
        raise ValueError(
            f"Leakage detected: forbidden keys in internal_state: {sorted(forbidden_found)}"
        )
