from __future__ import annotations

import random
from typing import Any, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEdge, SceneEntity
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class MotifGraphPattern(BasePattern):
    """
    Nodes: motifs. Edges: synchronicity / resonance.
    """

    kind = PatternKind.MOTIF_GRAPH

    def input_contract(self) -> Mapping[str, Any]:
        return {
            "motifs": "list[str] (preferred), else not_computable",
            "edges": "list[{source,target,magnitude,domain?}] (optional)",
        }

    def required_metrics(self) -> Tuple[str, ...]:
        return ("resonance_magnitude",)

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_motifs")

    def affordances(self) -> Tuple[str, ...]:
        return ("graph", "resonance_edges", "domain_color_family")

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        motifs = frame_payload.get("motifs")
        if not isinstance(motifs, list) or not motifs:
            inst = self._instance(
                pattern_id="motif_graph/v1", inputs={"motifs": motifs}, failure_mode="no_motifs"
            )
            return PatternBuildResult(
                instance=inst,
                entities=tuple(),
                edges=tuple(),
                fields=tuple(),
                time_axis=NC,
                animation_plan=AnimationPlan(kind="none", steps=tuple()),
                semantic_map_patch={},
                constraints_patch={},
            )

        motifs_s = tuple(sorted(str(m) for m in motifs))
        _rng = random.Random(seed ^ 0xA11CE)

        # Entities carry semantics only; layout is renderer responsibility.
        entities = tuple(
            SceneEntity(
                entity_id=f"motif:{m}",
                kind="motif",
                label=m,
                domain=str(frame_payload.get("domain") or "not_computable"),
                glyph_rune_id=str(frame_payload.get("glyph_map", {}).get(m) or NC),
                metrics={
                    "order": float(i),
                },
            )
            for i, m in enumerate(motifs_s)
        )

        edges_in = frame_payload.get("edges")
        edges: Tuple[SceneEdge, ...] = tuple()
        if isinstance(edges_in, list) and edges_in:
            tmp = []
            for i, e in enumerate(edges_in):
                if not isinstance(e, Mapping):
                    continue
                s = str(e.get("source"))
                t = str(e.get("target"))
                if not s or not t:
                    continue
                mag = e.get("magnitude", NC)
                tmp.append(
                    SceneEdge(
                        edge_id=f"edge:{i}:{s}->{t}",
                        source_id=f"motif:{s}",
                        target_id=f"motif:{t}",
                        kind=str(e.get("kind") or "synchronicity"),
                        domain=str(e.get("domain") or frame_payload.get("domain") or NC),
                        resonance_magnitude=float(mag) if isinstance(mag, (int, float)) else NC,
                        uncertainty=float(e.get("uncertainty"))
                        if isinstance(e.get("uncertainty"), (int, float))
                        else NC,
                    )
                )
            edges = tuple(sorted(tmp, key=lambda x: x.edge_id))

        inst = self._instance(
            pattern_id="motif_graph/v1",
            inputs={"motifs": motifs_s, "edges_present": bool(edges)},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=entities,
            edges=edges,
            fields=tuple(),
            time_axis=NC,
            animation_plan=AnimationPlan(kind="none", steps=tuple()),
            semantic_map_patch={
                "edge_thickness_semantics": "resonance_magnitude",
                "edge_color_semantics": "domain_family",
            },
            constraints_patch={},
        )
