from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioPolicy:
    schema_version: str
    source_cycle_id: str
    max_changes_per_cycle: int = 1

