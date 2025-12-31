from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class StabilizationState:
    """
    Tracks (module_id, knob_name) -> cycles_since_change.
    Deterministic, in-memory; persistence is a later feature.
    """
    cycles_since_change: Dict[Tuple[str, str], int]


def new_state() -> StabilizationState:
    return StabilizationState(cycles_since_change={})


def note_change(state: StabilizationState, module_id: str, knob_name: str) -> None:
    state.cycles_since_change[(module_id, knob_name)] = 0


def tick_cycle(state: StabilizationState) -> None:
    for k in list(state.cycles_since_change.keys()):
        state.cycles_since_change[k] += 1


def allowed_by_stabilization(state: StabilizationState, module_id: str, knob_name: str, required_cycles: int) -> bool:
    """
    If required_cycles == 0: always allowed.
    If we have no record: treat as stabilized (allowed) (conservative about false blocks).
    """
    if required_cycles <= 0:
        return True
    v = state.cycles_since_change.get((module_id, knob_name))
    if v is None:
        return True
    return v >= required_cycles
