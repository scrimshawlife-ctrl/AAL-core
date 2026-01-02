from __future__ import annotations

from typing import Any, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEntity, TimeAxis
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class TemporalBraidPattern(BasePattern):
    """
    Time-woven motif strands (discrete time steps).
    """

    kind = PatternKind.TEMPORAL_BRAID

    def input_contract(self) -> Mapping[str, Any]:
        return {
            "timeline": "list[{t, motifs: list[str]}] preferred; else not_computable",
        }

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_timeline")

    def affordances(self) -> Tuple[str, ...]:
        return ("timeline", "state_change_only_motion")

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        timeline = frame_payload.get("timeline")
        if not isinstance(timeline, list) or not timeline:
            inst = self._instance(
                pattern_id="temporal_braid/v1",
                inputs={"timeline": timeline},
                failure_mode="no_timeline",
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

        steps = []
        motifs_all = set()
        for item in timeline:
            if not isinstance(item, Mapping):
                continue
            t = str(item.get("t") or NC)
            motifs = item.get("motifs")
            if isinstance(motifs, list):
                ms = tuple(sorted(str(m) for m in motifs))
            else:
                ms = tuple()
            steps.append((t, ms))
            motifs_all.update(ms)

        steps_s = tuple(sorted(steps, key=lambda x: x[0]))
        motifs_s = tuple(sorted(motifs_all))

        # Entity per motif strand; renderer can weave it over time_axis.
        entities = tuple(
            SceneEntity(
                entity_id=f"motif:{m}",
                kind="motif",
                label=m,
                domain=str(frame_payload.get("domain") or NC),
                glyph_rune_id=str(frame_payload.get("glyph_map", {}).get(m) or NC),
                metrics={"order": float(i)},
            )
            for i, m in enumerate(motifs_s)
        )

        time_axis = TimeAxis(
            kind="discrete", t0_utc=str(steps_s[0][0]), steps=tuple(t for t, _ in steps_s)
        )
        # Animation is a proposal of steps, not a renderer directive (semantics preserved).
        anim_steps = tuple({"t": t, "motifs": list(ms)} for t, ms in steps_s)

        inst = self._instance(
            pattern_id="temporal_braid/v1",
            inputs={"steps": steps_s},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=entities,
            edges=tuple(),
            fields=tuple(),
            time_axis=time_axis,
            animation_plan=AnimationPlan(kind="timeline", steps=anim_steps),
            semantic_map_patch={
                "motion_semantics": "state_change_only",
                "decay_semantics": "signal_halflife_if_provided",
            },
            constraints_patch={},
        )
