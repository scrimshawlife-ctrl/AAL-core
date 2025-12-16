"""
Provenance tracking and input fingerprinting for audit trails.
"""
import json
import hashlib
from datetime import datetime
from typing import List
from .types import GameState, GameContext, MarketLine, Modifier, ProvenanceRecord


def fingerprint_inputs(ctx: GameContext, lines: List[MarketLine], mods: List[Modifier]) -> str:
    """
    Compute stable fingerprint of all inputs to a game execution.

    Args:
        ctx: GameContext
        lines: List of MarketLine instances
        mods: List of Modifier instances

    Returns:
        SHA256 hex digest of canonical JSON representation
    """
    # Build canonical representation
    inputs = {
        "context": {
            "game_id": ctx.game_id,
            "venue_id": ctx.venue_id,
            "home_away": ctx.home_away,
            "coach_id_home": ctx.coach_id_home,
            "coach_id_away": ctx.coach_id_away,
            "game_date": ctx.game_date,
            "days_rest_home": ctx.days_rest_home,
            "days_rest_away": ctx.days_rest_away,
            "travel_km_home": ctx.travel_km_home,
            "travel_km_away": ctx.travel_km_away,
        },
        "lines": [
            {"stat_name": line.stat_name, "line": line.line, "direction": line.direction}
            for line in lines
        ],
        "modifiers": [
            {
                "name": mod.name,
                "key": mod.key,
                "key_value": mod.key_value,
                "applies_to": sorted(mod.applies_to),
                "weight": mod.weight,
            }
            for mod in mods
        ],
    }

    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_provenance(
    state: GameState,
    ctx: GameContext,
    lines: List[MarketLine],
    mods: List[Modifier],
    version: str = "0.1.0"
) -> ProvenanceRecord:
    """
    Create a complete provenance record for a game execution.

    Args:
        state: The GameState after execution
        ctx: The GameContext used
        lines: The MarketLine inputs
        mods: The Modifier instances applied
        version: Code version string (deterministic placeholder)

    Returns:
        ProvenanceRecord with full audit trail
    """
    # Hash the modifier set
    mod_names = sorted([mod.name for mod in mods])
    mod_set_json = json.dumps(mod_names, sort_keys=True, separators=(",", ":"))
    mod_set_hash = hashlib.sha256(mod_set_json.encode("utf-8")).hexdigest()

    # Fingerprint all inputs
    inputs_fp = fingerprint_inputs(ctx, lines, mods)

    return ProvenanceRecord(
        timestamp_iso=datetime.utcnow().isoformat(),
        game_id=state.game_id,
        context_key_hash=state.context_key,
        modifier_set_hash=mod_set_hash,
        code_version=version,
        inputs_fingerprint=inputs_fp,
    )
