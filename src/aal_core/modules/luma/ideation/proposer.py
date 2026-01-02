from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

from ..contracts.enums import PatternKind
from ..contracts.provenance import sha256_hex
from .constraints import IdeationConstraints
from .novelty_score import NoveltyScore, score_proposal


@dataclass(frozen=True)
class PatternProposal:
    """
    A governed proposal for a novel visualization grammar.

    This is *not* generative art and is never applied by default.
    """

    proposal_id: str
    composed_of: Tuple[PatternKind, ...]
    semantic_justification: str
    readability_risks: Tuple[str, ...]
    score: NoveltyScore
    required_inputs: Tuple[str, ...]


def propose(
    *,
    constraints: IdeationConstraints,
    available_patterns: Sequence[PatternKind],
    baseline_semantics: Mapping[str, Any],
    failure_signals: Sequence[str],
) -> Tuple[PatternProposal, ...]:
    """
    Deterministically propose *compositions* of existing primitives.
    """

    if constraints.allow_new_primitives:
        # v1 forbids this; keep a hard guard even if someone toggles it.
        raise ValueError(
            "LUMA v1 forbids new primitives; proposals must compose existing patterns only."
        )

    avail = tuple(sorted(set(available_patterns), key=lambda k: k.value))
    failures = tuple(sorted(set(str(s) for s in failure_signals)))

    proposals = []

    def _mk(
        composed_of: Tuple[PatternKind, ...],
        justification: str,
        risks: Tuple[str, ...],
        required_inputs: Tuple[str, ...],
        proposal_semantics: Mapping[str, Any],
    ) -> None:
        sc = score_proposal(
            baseline_semantics=baseline_semantics,
            proposal_semantics=proposal_semantics,
            primitive_count=len(composed_of),
        )
        if sc.information_gain < constraints.min_information_gain:
            return
        if sc.cognitive_load > constraints.max_cognitive_load:
            return
        if sc.redundancy > constraints.max_redundancy:
            return
        pid = sha256_hex(
            {
                "composed_of": tuple(k.value for k in composed_of),
                "failures": failures,
                "justification": justification,
                "required_inputs": required_inputs,
            }
        )[:16]
        proposals.append(
            PatternProposal(
                proposal_id=f"proposal:{pid}",
                composed_of=composed_of,
                semantic_justification=justification,
                readability_risks=tuple(risks),
                score=sc,
                required_inputs=required_inputs,
            )
        )

    # Baseline guided heuristics (deterministic)
    failure_set = set(failures)

    if "no_timeline" in failure_set and PatternKind.MOTIF_GRAPH in avail:
        _mk(
            composed_of=(PatternKind.MOTIF_GRAPH,),
            justification=(
                "Timeline missing; fallback to motif adjacency graph preserves "
                "synchronicity semantics."
            ),
            risks=("may obscure temporal ordering",),
            required_inputs=("motifs", "edges(optional)"),
            proposal_semantics={"graph": True, "edge_thickness_semantics": "resonance_magnitude"},
        )

    if ("no_motifs" in failure_set or "no_edges" in failure_set) and (
        PatternKind.DOMAIN_LATTICE in avail and PatternKind.SANKEY_TRANSFER in avail
    ):
        _mk(
            composed_of=(PatternKind.DOMAIN_LATTICE, PatternKind.SANKEY_TRANSFER),
            justification=(
                "Motifs/edges missing; domain-level transfer can still express "
                "cross-domain structure."
            ),
            risks=("coarser abstraction may hide motif-level causality (not implied)",),
            required_inputs=("domains", "flows"),
            proposal_semantics={
                "layered_domains": True,
                "flow": True,
                "edge_thickness_semantics": "resonance_magnitude",
            },
        )

    if (
        "no_field" in failure_set
        and PatternKind.MOTIF_GRAPH in avail
        and PatternKind.CLUSTER_BLOOM in avail
    ):
        _mk(
            composed_of=(PatternKind.MOTIF_GRAPH, PatternKind.CLUSTER_BLOOM),
            justification=(
                "Scalar field missing; cluster bloom can encode emergent grouping "
                "while motif graph retains links."
            ),
            risks=("cluster heuristic may be arbitrary; treat as proposal",),
            required_inputs=("motifs", "edges(optional)", "clusters(optional)"),
            proposal_semantics={
                "clusters": True,
                "graph": True,
                "decay_semantics": "signal_halflife",
            },
        )

    proposals_s = tuple(sorted(proposals, key=lambda p: (-p.score.total, p.proposal_id)))
    return proposals_s
