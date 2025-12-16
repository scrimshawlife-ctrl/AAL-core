"""
Core data structures for deterministic game state management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass(frozen=True)
class GameContext:
    """
    Stable contextual variables for a single game.
    These are the keys used to select modifiers.
    """
    game_id: str
    venue_id: str
    home_away: str  # "home" or "away"
    coach_id_home: str
    coach_id_away: str
    game_date: str  # ISO format
    days_rest_home: Optional[int] = None
    days_rest_away: Optional[int] = None
    travel_km_home: Optional[float] = None
    travel_km_away: Optional[float] = None


@dataclass(frozen=True)
class MarketLine:
    """
    A single betting line or projection target.
    """
    stat_name: str
    line: float
    direction: str  # "over" or "under" (informational)


@dataclass(frozen=True)
class Modifier:
    """
    A contextual adjustment rule tied to specific key values.
    """
    name: str
    key: str  # The context dimension: "venue_id", "coach_id_home", etc.
    key_value: str  # The specific value: "MSG", "coach_123", etc.
    applies_to: List[str]  # Stat names this modifier affects
    weight: float  # Multiplicative adjustment: +0.03 => 1.03x
    notes: str = ""


@dataclass
class GameState:
    """
    The runtime state for a single game execution.
    Must be cold-started (empty internal_state) for each game.
    """
    game_id: str
    created_at: str  # ISO timestamp
    context_key: str  # Hash of the GameContext
    applied_modifiers: List[str] = field(default_factory=list)  # Modifier names
    internal_state: Dict[str, Any] = field(default_factory=dict)  # Must start empty


@dataclass(frozen=True)
class ProvenanceRecord:
    """
    Full audit trail for a game execution.
    """
    timestamp_iso: str
    game_id: str
    context_key_hash: str
    modifier_set_hash: str
    code_version: str
    inputs_fingerprint: str


@dataclass(frozen=True)
class RunResult:
    """
    Complete output of a game execution.
    """
    state: GameState
    provenance: ProvenanceRecord
    adjusted_lines: List[MarketLine]
