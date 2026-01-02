from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class NoveltyScore:
    """
    Deterministic scoring for proposal ranking.
    """

    information_gain: float  # 0..1
    cognitive_load: float  # 0..1 (lower is better)
    redundancy: float  # 0..1 (lower is better)
    total: float  # higher is better


def score_proposal(
    *,
    baseline_semantics: Mapping[str, Any],
    proposal_semantics: Mapping[str, Any],
    primitive_count: int,
) -> NoveltyScore:
    """
    Simple, deterministic heuristic:
    - Information gain approximated by new semantic keys introduced.
    - Cognitive load increases with primitive count and semantic map size.
    - Redundancy increases with overlap against baseline semantics.
    """

    b_keys = tuple(sorted(str(k) for k in baseline_semantics.keys()))
    p_keys = tuple(sorted(str(k) for k in proposal_semantics.keys()))

    b_set = set(b_keys)
    p_set = set(p_keys)

    new_keys = p_set - b_set
    overlap = p_set & b_set

    information_gain = 0.0 if not p_set else min(1.0, len(new_keys) / max(1, len(p_set)))
    redundancy = 0.0 if not p_set else min(1.0, len(overlap) / max(1, len(p_set)))

    # Cognitive load: primitives pay rent; keep bounded.
    cognitive_load = min(1.0, 0.15 * max(1, primitive_count) + 0.02 * len(p_set))

    total = max(0.0, information_gain - 0.7 * cognitive_load - 0.5 * redundancy)
    return NoveltyScore(
        information_gain=information_gain,
        cognitive_load=cognitive_load,
        redundancy=redundancy,
        total=total,
    )
