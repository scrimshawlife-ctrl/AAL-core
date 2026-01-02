from __future__ import annotations

from typing import Any, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEdge, SceneEntity
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class ClusterBloomPattern(BasePattern):
    """
    Emergent motif clusters with expansion/decay (semantic proposal).
    """

    kind = PatternKind.CLUSTER_BLOOM

    def input_contract(self) -> Mapping[str, Any]:
        return {
            "motifs": "list[str] required",
            "clusters": "optional list[{cluster_id, motifs[]}]",
            "halflife": "optional float (seconds) for decay semantics",
        }

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_motifs")

    def affordances(self) -> Tuple[str, ...]:
        return ("clusters", "decay_animation_semantics")

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        motifs = frame_payload.get("motifs")
        if not isinstance(motifs, list) or not motifs:
            inst = self._instance(
                pattern_id="cluster_bloom/v1", inputs={"motifs": motifs}, failure_mode="no_motifs"
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
        clusters = frame_payload.get("clusters")

        # If clusters aren't provided, use a deterministic heuristic:
        # cluster by first character (keeps it explainable and deterministic).
        cluster_map = {}
        if isinstance(clusters, list) and clusters:
            for c in clusters:
                if not isinstance(c, Mapping):
                    continue
                cid = str(c.get("cluster_id") or NC)
                ms = c.get("motifs")
                if isinstance(ms, list):
                    cluster_map[cid] = tuple(sorted(str(m) for m in ms))
        else:
            tmp = {}
            for m in motifs_s:
                k = (m[0] if m else "_").lower()
                tmp.setdefault(k, []).append(m)
            cluster_map = {f"cluster:{k}": tuple(v) for k, v in sorted(tmp.items())}

        entities = []
        for i, (cid, ms) in enumerate(sorted(cluster_map.items(), key=lambda kv: kv[0])):
            entities.append(
                SceneEntity(
                    entity_id=f"{cid}",
                    kind="cluster",
                    label=cid,
                    domain=str(frame_payload.get("domain") or NC),
                    glyph_rune_id=NC,
                    metrics={"order": float(i), "size": float(len(ms))},
                )
            )
            for m in ms:
                entities.append(
                    SceneEntity(
                        entity_id=f"motif:{m}",
                        kind="motif",
                        label=m,
                        domain=str(frame_payload.get("domain") or NC),
                        glyph_rune_id=str(frame_payload.get("glyph_map", {}).get(m) or NC),
                        metrics={"order": float(i)},
                    )
                )

        # Containment edges from cluster -> motif
        edges = []
        for cid, ms in sorted(cluster_map.items(), key=lambda kv: kv[0]):
            for j, m in enumerate(ms):
                edges.append(
                    SceneEdge(
                        edge_id=f"contains:{cid}:{m}",
                        source_id=cid,
                        target_id=f"motif:{m}",
                        kind="contains",
                        domain=str(frame_payload.get("domain") or NC),
                        resonance_magnitude=NC,
                        uncertainty=NC,
                    )
                )

        halflife = frame_payload.get("halflife", NC)
        hl = float(halflife) if isinstance(halflife, (int, float)) else NC

        inst = self._instance(
            pattern_id="cluster_bloom/v1",
            inputs={"clusters": tuple(sorted(cluster_map.items())), "halflife": hl},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=tuple(entities),
            edges=tuple(sorted(edges, key=lambda e: e.edge_id)),
            fields=tuple(),
            time_axis=NC,
            animation_plan=AnimationPlan(kind="none", steps=tuple()),
            semantic_map_patch={
                "decay_semantics": "signal_halflife",
                "halflife_seconds": hl,
            },
            constraints_patch={},
        )
