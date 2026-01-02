from __future__ import annotations

from typing import Any, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEdge, SceneEntity
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class TransferChordPattern(BasePattern):
    """
    Domains on a ring; transfer edges become arcs.
    """

    kind = PatternKind.TRANSFER_CHORD

    def input_contract(self) -> Mapping[str, Any]:
        return {"flows": "list[{source_domain,target_domain,value,uncertainty?}] preferred"}

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_flows")

    def affordances(self) -> Tuple[str, ...]:
        return ("flow", "chord", "width_value", "uncertainty_alpha")

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        flows = frame_payload.get("flows")
        if not isinstance(flows, list) or not flows:
            inst = self._instance(
                pattern_id="transfer_chord/v1",
                inputs={"flows": flows},
                failure_mode="no_flows",
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

        doms = set()
        edges = []
        for i, f in enumerate(flows):
            if not isinstance(f, Mapping):
                continue
            sd = str(f.get("source_domain") or NC)
            td = str(f.get("target_domain") or NC)
            doms.add(sd)
            doms.add(td)
            v = f.get("value", NC)
            mag = float(v) if isinstance(v, (int, float)) else NC
            unc = f.get("uncertainty", NC)
            u = float(unc) if isinstance(unc, (int, float)) else NC
            edges.append(
                SceneEdge(
                    edge_id=f"flow:{i}:{sd}->{td}",
                    source_id=f"domain:{sd}",
                    target_id=f"domain:{td}",
                    kind="transfer",
                    domain=sd,
                    resonance_magnitude=mag,
                    uncertainty=u,
                )
            )

        doms_s = tuple(sorted(doms))
        entities = tuple(
            SceneEntity(
                entity_id=f"domain:{d}",
                kind="domain",
                label=d,
                domain=d,
                glyph_rune_id=NC,
                metrics={"order": float(i)},
            )
            for i, d in enumerate(doms_s)
        )

        inst = self._instance(
            pattern_id="transfer_chord/v1",
            inputs={"domains": doms_s, "flows_n": len(edges)},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=entities,
            edges=tuple(sorted(edges, key=lambda e: e.edge_id)),
            fields=tuple(),
            time_axis=NC,
            animation_plan=AnimationPlan(kind="none", steps=tuple()),
            semantic_map_patch={
                "edge_thickness_semantics": "resonance_magnitude",
                "transparency_semantics": "uncertainty",
            },
            constraints_patch={},
        )
