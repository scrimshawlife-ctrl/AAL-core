from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ..contracts.enums import PatternKind, ProposalStatus
from ..contracts.proposal_ir import PatternProposal
from ..contracts.provenance import sha256_hex
from ..contracts.scene_ir import LumaSceneIR
from .constraints import IdeationConstraints
from .constraints import validate_pattern_spec
from .novelty_score import NoveltyScore, score_composition, score_proposal


@dataclass(frozen=True)
class CompositionProposal:
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
) -> Tuple[CompositionProposal, ...]:
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
        sc = score_composition(
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
            CompositionProposal(
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


@dataclass(frozen=True)
class ProposerConfig:
    max_proposals: int = 3
    allow_primitives: List[str] | None = None
    limits: Dict[str, Any] | None = None


class PatternProposer:
    proposer_id = "luma.ideation.proposer"
    proposer_version = "0.1.0"

    def propose(
        self,
        scene: LumaSceneIR,
        baseline_patterns: List[str],
        cfg: ProposerConfig | None = None,
    ) -> List[PatternProposal]:
        cfg = cfg or ProposerConfig()
        scene_hash = scene.hash

        entities = () if isinstance(scene.entities, str) else scene.entities
        edges = () if isinstance(scene.edges, str) else scene.edges
        time_axis = None if isinstance(scene.time_axis, str) else scene.time_axis

        has_domains = any(e.kind == "domain" for e in entities)
        has_transfers = any(ed.kind == "transfer" for ed in edges)
        has_time = time_axis is not None and bool(time_axis.steps)
        motif_count = sum(1 for e in entities if e.kind == "motif")
        pairs = set()
        for ed in edges:
            if ed.kind != "transfer":
                continue
            src = ed.source_id
            tgt = ed.target_id
            if isinstance(src, str) and isinstance(tgt, str):
                pairs.add((src, tgt))
        transfer_pair_count = len(pairs)
        transfer_view_reco = "sankey" if transfer_pair_count <= 8 else "chord"

        candidates: List[Dict[str, Any]] = []

        if has_domains and has_transfers:
            candidates.append(
                {
                    "id_hint": "chord_transfer",
                    "primitives": ["chord", "matrix"],
                    "layers": ["domain_nodes", "transfer_arcs"],
                    "channels": {
                        "arc_thickness": "edge.resonance_magnitude",
                        "opacity": "edge.resonance_magnitude",
                    },
                    "mappings": [
                        {"source": "edge.source_id", "target": "chord.source"},
                        {"source": "edge.target_id", "target": "chord.target"},
                        {"source": "edge.resonance_magnitude", "target": "chord.value"},
                    ],
                    "intent": (
                        "Reduce clutter vs sankey when transfers are dense by using "
                        "chord/matrix views."
                    ),
                    "gating_hint": {"prefer_when_transfer_pairs_gt": 8},
                }
            )

        if has_domains and motif_count >= 6:
            candidates.append(
                {
                    "id_hint": "motif_domain_matrix",
                    "primitives": ["matrix", "heatmap"],
                    "layers": ["motifs_rows", "domains_cols", "cells"],
                    "channels": {"cell_opacity": "entity.metrics.salience"},
                    "mappings": [
                        {"source": "entity.domain", "target": "matrix.col"},
                        {"source": "entity.kind", "target": "matrix.row_group"},
                        {"source": "entity.metrics.salience", "target": "heatmap.value"},
                    ],
                    "intent": (
                        "Expose motif distribution across domains as an incidence/heatmap."
                    ),
                }
            )

        if has_time and motif_count >= 4:
            candidates.append(
                {
                    "id_hint": "motif_timeline",
                    "primitives": ["timeline", "nodes", "edges"],
                    "layers": ["time_ticks", "motif_lanes", "links"],
                    "channels": {"link_opacity": "edge.resonance_magnitude"},
                    "mappings": [
                        {"source": "time_axis.steps", "target": "timeline.x"},
                        {"source": "entity.metrics.order", "target": "lanes.order"},
                        {"source": "edge.resonance_magnitude", "target": "edges.weight"},
                    ],
                    "intent": "Surface motif coherence over time without implying causality.",
                }
            )

        if cfg.allow_primitives:
            allow = set(cfg.allow_primitives)
            candidates = [
                c for c in candidates if all(p in allow for p in c["primitives"])
            ]

        proposals: List[PatternProposal] = []
        for c in sorted(candidates, key=lambda x: x["id_hint"]):
            spec = {
                "pattern_id": f"proposal.{c['id_hint']}",
                "primitives": c["primitives"],
                "layers": c["layers"],
                "channels": c["channels"],
                "mappings": c["mappings"],
                "intent": c["intent"],
                "claims": [],
            }
            validate_pattern_spec(spec, cfg.limits)
            scores = score_proposal(spec, baseline_patterns)

            pid_src = json.dumps(
                {"scene_hash": scene_hash, "spec": spec},
                sort_keys=True,
                separators=(",", ":"),
            )
            proposal_id = hashlib.sha256(pid_src.encode("utf-8")).hexdigest()[:16]

            proposals.append(
                PatternProposal(
                    proposal_id=proposal_id,
                    base_patterns=list(sorted(set(baseline_patterns))),
                    pattern_spec=spec,
                    justification={
                        "intent": c["intent"],
                        "pressure_signals": {
                        "has_domains": has_domains,
                        "has_transfers": has_transfers,
                        "has_time": has_time,
                        "motif_count": motif_count,
                        "transfer_pair_count": transfer_pair_count,
                        "transfer_view_recommendation": transfer_view_reco,
                        "thresholds": {"sankey_max_pairs": 8},
                    },
                },
                    scores=scores,
                    risks={
                        "cognitive_load": (
                            "medium" if scores["readability"] < 0.7 else "low"
                        ),
                        "misread_risk": (
                            "matrix/chord may imply symmetry; label as aggregated transfer"
                        ),
                        "failure_modes": [
                            "sparse data yields empty cells/arcs",
                            "dense labels increase text noise",
                        ],
                    },
                    provenance={
                        "scene_hash": scene_hash,
                        "proposer": {
                            "id": self.proposer_id,
                            "version": self.proposer_version,
                        },
                        "config": cfg.__dict__,
                        "baseline_patterns": list(sorted(set(baseline_patterns))),
                    },
                    status=ProposalStatus.PROPOSED.value,
                )
            )

        proposals.sort(
            key=lambda p: (-float(p.scores.get("info_gain", 0.0)), p.proposal_id)
        )
        return proposals[:max(0, int(cfg.max_proposals))]
