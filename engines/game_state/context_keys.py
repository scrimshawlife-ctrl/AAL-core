"""
Context key building and deterministic hashing.
"""
import json
import hashlib
from typing import Dict, Any
from .types import GameContext


def build_context_key(ctx: GameContext) -> Dict[str, Any]:
    """
    Build a stable dictionary representation of the game context.

    Args:
        ctx: GameContext instance

    Returns:
        Dictionary with all context fields (excluding game_id)
    """
    key = {
        "venue_id": ctx.venue_id,
        "home_away": ctx.home_away,
        "coach_id_home": ctx.coach_id_home,
        "coach_id_away": ctx.coach_id_away,
        "game_date": ctx.game_date,
    }

    # Include optional fields if present
    if ctx.days_rest_home is not None:
        key["days_rest_home"] = ctx.days_rest_home
    if ctx.days_rest_away is not None:
        key["days_rest_away"] = ctx.days_rest_away
    if ctx.travel_km_home is not None:
        key["travel_km_home"] = ctx.travel_km_home
    if ctx.travel_km_away is not None:
        key["travel_km_away"] = ctx.travel_km_away

    return key


def hash_key(key: Dict[str, Any]) -> str:
    """
    Compute deterministic SHA256 hash of a context key.

    Args:
        key: Dictionary to hash

    Returns:
        Hex digest string (64 characters)
    """
    # Ensure stable ordering and formatting
    canonical = json.dumps(key, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
