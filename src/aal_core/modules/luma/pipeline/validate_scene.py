from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from ..contracts.enums import NotComputable
from ..contracts.scene_ir import LumaSceneIR

NC = NotComputable.VALUE.value

_RUNE_ID_RE = re.compile(r"^[0-9]{4}$")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


def validate_scene(scene: LumaSceneIR) -> ValidationResult:
    """
    Enforce canonical constraints:
    - explicit not_computable
    - semantics law: uncertainty in [0,1], resonance magnitude >= 0
    - glyphs must be ABX-Runes identifiers or not_computable
    """

    errors: List[str] = []
    warnings: List[str] = []

    if not scene.scene_id:
        errors.append("scene_id missing")
    if not scene.hash:
        errors.append("scene.hash missing")
    if scene.seed < 0:
        errors.append("seed must be non-negative")

    if isinstance(scene.entities, str):
        if scene.entities != NC:
            errors.append("entities must be tuple[...] or not_computable")
    else:
        seen = set()
        for e in scene.entities:
            if e.entity_id in seen:
                errors.append(f"duplicate entity_id: {e.entity_id}")
            seen.add(e.entity_id)
            if e.glyph_rune_id != NC and not _RUNE_ID_RE.match(str(e.glyph_rune_id)):
                gid = str(e.glyph_rune_id)
                errors.append(f"glyph_rune_id must be ABX-Runes id (0000) or not_computable: {gid}")

    if isinstance(scene.edges, str):
        if scene.edges != NC:
            errors.append("edges must be tuple[...] or not_computable")
    else:
        for ed in scene.edges:
            if (
                isinstance(ed.resonance_magnitude, (int, float))
                and float(ed.resonance_magnitude) < 0.0
            ):
                errors.append(f"edge resonance_magnitude must be >= 0: {ed.edge_id}")
            if isinstance(ed.uncertainty, (int, float)):
                u = float(ed.uncertainty)
                if u < 0.0 or u > 1.0:
                    errors.append(f"edge uncertainty must be in [0,1]: {ed.edge_id}")

    if isinstance(scene.fields, str):
        if scene.fields != NC:
            errors.append("fields must be tuple[...] or not_computable")
    else:
        for f in scene.fields:
            if f.grid_w < 0 or f.grid_h < 0:
                errors.append(f"field grid dims must be non-negative: {f.field_id}")
            if not isinstance(f.values, str):
                if len(f.values) != f.grid_w * f.grid_h:
                    errors.append(f"field values length mismatch: {f.field_id}")
            if not isinstance(f.uncertainty, str):
                if len(f.uncertainty) != f.grid_w * f.grid_h:
                    errors.append(f"field uncertainty length mismatch: {f.field_id}")

    # Visual semantic law sanity checks (documented in docs/visual_semantics.md)
    if scene.semantic_map.get("edge_thickness_semantics") == "resonance_magnitude":
        if isinstance(scene.edges, str):
            warnings.append("edge_thickness_semantics set but edges are not_computable")

    ok = not errors
    return ValidationResult(ok=ok, errors=tuple(errors), warnings=tuple(warnings))
