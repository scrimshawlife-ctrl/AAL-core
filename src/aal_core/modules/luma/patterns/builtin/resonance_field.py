from __future__ import annotations

from typing import Any, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneField
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class ResonanceFieldPattern(BasePattern):
    """
    Scalar resonance field over a domain space (grid).
    """

    kind = PatternKind.RESONANCE_FIELD

    def input_contract(self) -> Mapping[str, Any]:
        return {
            "field": "{grid_w, grid_h, values[]} (row-major) preferred",
            "field_uncertainty": "{uncertainty[]} optional per-cell",
        }

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_field")

    def affordances(self) -> Tuple[str, ...]:
        return ("scalar_field", "uncertainty_alpha")

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        field = frame_payload.get("field")
        if not isinstance(field, Mapping):
            inst = self._instance(
                pattern_id="resonance_field/v1", inputs={"field": field}, failure_mode="no_field"
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

        w = field.get("grid_w")
        h = field.get("grid_h")
        vals = field.get("values")
        if not isinstance(w, int) or not isinstance(h, int) or not isinstance(vals, list):
            inst = self._instance(
                pattern_id="resonance_field/v1",
                inputs={"grid_w": w, "grid_h": h, "values_present": isinstance(vals, list)},
                failure_mode="not_computable",
            )
            return PatternBuildResult(
                instance=inst,
                entities=tuple(),
                edges=tuple(),
                fields=tuple(
                    [
                        SceneField(
                            field_id="field:resonance",
                            kind="scalar_field",
                            domain=str(frame_payload.get("domain") or NC),
                            grid_w=int(w) if isinstance(w, int) else 0,
                            grid_h=int(h) if isinstance(h, int) else 0,
                            values=NC,
                            uncertainty=NC,
                        )
                    ]
                ),
                time_axis=NC,
                animation_plan=AnimationPlan(kind="none", steps=tuple()),
                semantic_map_patch={"transparency_semantics": "uncertainty"},
                constraints_patch={},
            )

        unc = frame_payload.get("field_uncertainty")
        unc_vals = None
        if isinstance(unc, Mapping):
            u = unc.get("uncertainty")
            if isinstance(u, list) and len(u) == len(vals):
                unc_vals = tuple(float(x) if isinstance(x, (int, float)) else 1.0 for x in u)

        values_t = tuple(float(x) if isinstance(x, (int, float)) else 0.0 for x in vals)
        field_ir = SceneField(
            field_id="field:resonance",
            kind="scalar_field",
            domain=str(frame_payload.get("domain") or NC),
            grid_w=w,
            grid_h=h,
            values=values_t,
            uncertainty=unc_vals if unc_vals is not None else NC,
        )

        inst = self._instance(
            pattern_id="resonance_field/v1",
            inputs={"grid_w": w, "grid_h": h, "n": len(values_t)},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=tuple(),
            edges=tuple(),
            fields=(field_ir,),
            time_axis=NC,
            animation_plan=AnimationPlan(kind="none", steps=tuple()),
            semantic_map_patch={"transparency_semantics": "uncertainty"},
            constraints_patch={},
        )
