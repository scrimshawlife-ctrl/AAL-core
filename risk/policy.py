"""
Policy enforcement for parlay risk management.

Validates and filters legs based on entropy-derived limits.
"""
from dataclasses import dataclass
from typing import List, Dict, Any
from collections import Counter
from normalizers.types import SportNormalizerConfig
from .throttle import recommend_limits


@dataclass(frozen=True)
class LegSpec:
    """
    Minimal leg specification for policy enforcement.

    Does not depend on HollerSports types.
    """
    sport_id: str
    stat_id: str
    team_id: str
    primitive: str  # "opportunity", "usage", "hybrid", "event"
    survivability_score: float


def enforce_policy(
    cfg: SportNormalizerConfig,
    mode: str,
    legs: List[LegSpec]
) -> Dict[str, Any]:
    """
    Enforce parlay policy based on sport entropy and mode.

    Validates leg count, event primitives, same-team limits, and survivability.
    Returns deterministic drop recommendations for violating legs.

    Args:
        cfg: SportNormalizerConfig instance
        mode: Policy mode (ultra_safe, balanced, correlated, ladder)
        legs: List of LegSpec instances

    Returns:
        Dictionary with:
        - ok: bool (True if all legs pass)
        - reasons: list[str] (violation descriptions)
        - recommended_max_legs: int
        - dropped_indices: list[int] (legs to drop, in order)
        - passed_count: int
        - failed_count: int
    """
    # Get limits for this sport/mode
    limits = recommend_limits(cfg, mode)

    max_legs = limits["max_legs"]
    min_survivability = limits["min_survivability"]
    allow_event_primitives = limits["allow_event_primitives"]
    max_same_team = limits["max_same_team_legs"]
    max_high_var = limits["max_high_variance_legs"]

    reasons = []
    dropped_indices = []

    # Check 1: Event primitives in ultra_safe or high entropy
    if not allow_event_primitives:
        event_indices = [
            i for i, leg in enumerate(legs)
            if leg.primitive == "event"
        ]
        if event_indices:
            dropped_indices.extend(event_indices)
            reasons.append(
                f"Event primitives not allowed in mode '{mode}' "
                f"(entropy {limits['entropy_score']:.3f}). "
                f"Dropped {len(event_indices)} leg(s)."
            )

    # Check 2: Survivability below threshold
    low_surv_indices = [
        i for i, leg in enumerate(legs)
        if leg.survivability_score < min_survivability
        and i not in dropped_indices
    ]
    if low_surv_indices:
        # In ultra_safe, drop all low survivability
        # In other modes, allow up to max_high_variance_legs
        if mode == "ultra_safe" or len(low_surv_indices) > max_high_var:
            # Sort by survivability (lowest first) and drop excess
            low_surv_with_scores = [
                (i, legs[i].survivability_score)
                for i in low_surv_indices
            ]
            low_surv_with_scores.sort(key=lambda x: x[1])

            num_to_drop = (
                len(low_surv_indices) if mode == "ultra_safe"
                else len(low_surv_indices) - max_high_var
            )

            for i in range(num_to_drop):
                idx = low_surv_with_scores[i][0]
                if idx not in dropped_indices:
                    dropped_indices.append(idx)

            reasons.append(
                f"Survivability below {min_survivability:.2f} threshold. "
                f"Dropped {num_to_drop} leg(s)."
            )

    # Check 3: Same-team leg limit
    remaining_legs = [
        leg for i, leg in enumerate(legs)
        if i not in dropped_indices
    ]
    team_counts = Counter(leg.team_id for leg in remaining_legs)

    for team_id, count in team_counts.items():
        if count > max_same_team:
            # Find legs for this team (not already dropped)
            team_leg_indices = [
                i for i, leg in enumerate(legs)
                if leg.team_id == team_id and i not in dropped_indices
            ]

            # Sort by survivability (lowest first)
            team_legs_with_scores = [
                (i, legs[i].survivability_score)
                for i in team_leg_indices
            ]
            team_legs_with_scores.sort(key=lambda x: x[1])

            # Drop excess (lowest survivability first)
            num_to_drop = count - max_same_team
            for i in range(num_to_drop):
                idx = team_legs_with_scores[i][0]
                if idx not in dropped_indices:
                    dropped_indices.append(idx)

            reasons.append(
                f"Team '{team_id}' exceeds max {max_same_team} legs. "
                f"Dropped {num_to_drop} leg(s)."
            )

    # Check 4: Total leg count
    remaining_count = len(legs) - len(dropped_indices)
    if remaining_count > max_legs:
        # Need to drop more legs
        remaining_indices = [
            i for i in range(len(legs))
            if i not in dropped_indices
        ]

        # Sort by survivability (lowest first)
        remaining_with_scores = [
            (i, legs[i].survivability_score)
            for i in remaining_indices
        ]
        remaining_with_scores.sort(key=lambda x: x[1])

        # Drop excess
        num_to_drop = remaining_count - max_legs
        for i in range(num_to_drop):
            idx = remaining_with_scores[i][0]
            if idx not in dropped_indices:
                dropped_indices.append(idx)

        reasons.append(
            f"Total legs ({remaining_count}) exceeds max {max_legs}. "
            f"Dropped {num_to_drop} lowest-survivability leg(s)."
        )

    # Determine if policy passes
    ok = len(dropped_indices) == 0
    passed_count = len(legs) - len(dropped_indices)
    failed_count = len(dropped_indices)

    # Sort dropped_indices for determinism
    dropped_indices.sort()

    return {
        "ok": ok,
        "reasons": reasons,
        "recommended_max_legs": max_legs,
        "dropped_indices": dropped_indices,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "limits": limits,
    }
