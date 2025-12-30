from __future__ import annotations

from dataclasses import dataclass

from .schema import Lane, NodeKind, PlanOptions, Realm


class OutputMode:
    ORACLE_LOG = "oracle_log"
    RITUAL_MAP = "ritual_map"
    ANALYST_CONSOLE = "analyst_console"


def options_for_mode(mode: str) -> PlanOptions:
    """
    Deterministic mode routing for planning (not execution).
    Evidence gating rule is handled by upstream renderers; here we only prune topology.
    """
    if mode == OutputMode.ORACLE_LOG:
        # Typical: prefer forecast lane + artifacts; allow neutral dependencies
        return PlanOptions(
            include_lanes=(Lane.FORECAST, Lane.NEUTRAL),
            allow_deprecated=False,
            allow_archived=False,
        )

    if mode == OutputMode.RITUAL_MAP:
        # Show everything, including shadow, for "map" views
        return PlanOptions(
            include_lanes=(Lane.SHADOW, Lane.FORECAST, Lane.NEUTRAL),
            allow_deprecated=True,
            allow_archived=True,
        )

    if mode == OutputMode.ANALYST_CONSOLE:
        # Analyst view: include shadow + forecast, but usually exclude final artifacts
        return PlanOptions(
            include_lanes=(Lane.SHADOW, Lane.FORECAST, Lane.NEUTRAL),
            include_kinds=(NodeKind.ROOT_POLICY, NodeKind.KERNEL, NodeKind.REALM, NodeKind.RUNE),
            allow_deprecated=True,
            allow_archived=False,
        )

    # default conservative
    return PlanOptions()
