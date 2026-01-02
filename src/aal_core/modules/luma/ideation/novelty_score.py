from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class NoveltyScore:
    """
    Deterministic scoring for proposal ranking.
    """

    information_gain: float  # 0..1
    cognitive_load: float  # 0..1 (lower is better)
    redundancy: float  # 0..1 (lower is better)
    total: float  # higher is better


def score_composition(
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


def _clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def score_proposal(spec: Dict[str, Any], baseline_patterns: List[str]) -> Dict[str, float]:
    """
    Deterministic scoring heuristics.
    - novelty: adds a structural view not covered by baseline
    - readability: penalize too many primitives/channels/layers
    - redundancy: penalize overlap with baseline
    """
    primitives = spec.get("primitives", [])
    layers = spec.get("layers", [])
    channels = spec.get("channels", {})

    c = len(primitives) * 0.35 + len(layers) * 0.25 + len(channels) * 0.18
    readability = _clamp(1.0 - c)

    baseline = set(baseline_patterns)
    novelty_bonus = 0.0
    if "matrix" in primitives and "domain_lattice" in baseline:
        novelty_bonus += 0.22
    if "chord" in primitives and "sankey_transfer" in baseline:
        novelty_bonus += 0.22
    if "heatmap" in primitives and "resonance_field" not in baseline:
        novelty_bonus += 0.18
    if "radial" in primitives and "motif_graph" in baseline:
        novelty_bonus += 0.15
    novelty = _clamp(0.35 + novelty_bonus)

    redundant = 0.0
    if "grid" in primitives and "domain_lattice" in baseline:
        redundant += 0.25
    if "flows" in primitives and "sankey_transfer" in baseline:
        redundant += 0.25
    if "timeline" in primitives and "temporal_braid" in baseline:
        redundant += 0.25
    redundancy = _clamp(redundant)

    info_gain = _clamp(novelty * readability * (1.0 - redundancy))

    return {
        "novelty": float(novelty),
        "readability": float(readability),
        "redundancy": float(redundancy),
        "info_gain": float(info_gain),
    }
