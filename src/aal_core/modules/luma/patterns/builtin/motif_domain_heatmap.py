from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEntity
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class MotifDomainHeatmapPattern(BasePattern):
    """
    Motif×domain incidence heatmap (rows=motifs, columns=domains).
    """

    kind = PatternKind.MOTIF_DOMAIN_HEATMAP

    def input_contract(self) -> Mapping[str, Any]:
        return {
            "motifs": "list[str] or list[{id,domain_id,salience?}]",
            "domains": "list[str]",
        }

    def required_metrics(self) -> Tuple[str, ...]:
        return ("salience",)

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_motifs", "no_domains")

    def affordances(self) -> Tuple[str, ...]:
        return ("matrix", "heatmap", "motif_domain_incidence")

    def _iter_domains(self, domains_in: Iterable[Any]) -> Tuple[str, ...]:
        domains = []
        for d in domains_in:
            if isinstance(d, str):
                domains.append(d)
            elif isinstance(d, Mapping):
                dom = d.get("domain")
                if dom is not None:
                    domains.append(str(dom))
        return tuple(sorted(set(domains)))

    def _iter_motifs(self, motifs_in: Iterable[Any]) -> Tuple[Dict[str, Any], ...]:
        out = []
        for m in motifs_in:
            if isinstance(m, str):
                out.append(
                    {
                        "id": m,
                        "label": m,
                        "domain_id": NC,
                        "salience": NC,
                    }
                )
            elif isinstance(m, Mapping):
                mid = m.get("id") or m.get("motif") or m.get("label")
                if mid is None:
                    continue
                out.append(
                    {
                        "id": str(mid),
                        "label": str(m.get("label") or mid),
                        "domain_id": str(m.get("domain_id") or m.get("domain") or NC),
                        "salience": m.get("salience", NC),
                    }
                )
        return tuple(out)

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        motifs_in = frame_payload.get("motifs")
        if not isinstance(motifs_in, list) or not motifs_in:
            inst = self._instance(
                pattern_id="motif_domain_heatmap/v1",
                inputs={"motifs": motifs_in},
                failure_mode="no_motifs",
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

        domains_in = frame_payload.get("domains")
        if not isinstance(domains_in, list) or not domains_in:
            inst = self._instance(
                pattern_id="motif_domain_heatmap/v1",
                inputs={"domains": domains_in},
                failure_mode="no_domains",
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

        motifs = self._iter_motifs(motifs_in)
        domains = self._iter_domains(domains_in)

        motif_entities = []
        for i, m in enumerate(sorted(motifs, key=lambda x: x["id"])):
            sal = m.get("salience", NC)
            salience = float(sal) if isinstance(sal, (int, float)) else NC
            motif_entities.append(
                SceneEntity(
                    entity_id=f"motif:{m['id']}",
                    kind="motif",
                    label=m["label"],
                    domain=str(m.get("domain_id") or NC),
                    glyph_rune_id=str(frame_payload.get("glyph_map", {}).get(m["id"]) or NC),
                    metrics={
                        "order": float(i),
                        "salience": salience,
                    },
                )
            )

        domain_entities = tuple(
            SceneEntity(
                entity_id=f"domain:{d}",
                kind="domain",
                label=d,
                domain=d,
                glyph_rune_id=NC,
                metrics={"order": float(i)},
            )
            for i, d in enumerate(domains)
        )

        inst = self._instance(
            pattern_id="motif_domain_heatmap/v1",
            inputs={"motifs": tuple(m["id"] for m in motifs), "domains": domains},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=tuple(motif_entities) + domain_entities,
            edges=tuple(),
            fields=tuple(),
            time_axis=NC,
            animation_plan=AnimationPlan(kind="none", steps=tuple()),
            semantic_map_patch={
                "heatmap_semantics": "motif_domain_salience",
                "cell_opacity_semantics": "salience",
            },
            constraints_patch={},
        )
