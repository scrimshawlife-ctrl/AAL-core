import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.enums import NotComputable
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance
from aal_core.modules.luma.contracts.scene_ir import AnimationPlan, LumaSceneIR, SceneEntity
from aal_core.modules.luma.renderers.animation_plan import render_animation_plan

NC = NotComputable.VALUE.value


def _scene() -> LumaSceneIR:
    prov = SourceFrameProvenance(
        module="test.luma",
        utc="2026-01-02T00:00:00Z",
        payload_sha256="0" * 64,
        vendor_lock_sha256="1" * 64,
        manifest_sha256="2" * 64,
        abx_runes_used=tuple(),
        abx_runes_gate_state="CLEAR",
    )
    entities = (
        SceneEntity(
            entity_id="domain:alpha",
            kind="domain",
            label="Alpha",
            domain="alpha",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        SceneEntity(
            entity_id="domain:beta",
            kind="domain",
            label="Beta",
            domain="beta",
            glyph_rune_id=NC,
            metrics={"order": 1.0},
        ),
        SceneEntity(
            entity_id="motif:m1",
            kind="motif",
            label="M1",
            domain="alpha",
            glyph_rune_id=NC,
            metrics={"order": 2.0, "salience": 0.8},
        ),
        SceneEntity(
            entity_id="motif:m2",
            kind="motif",
            label="M2",
            domain="beta",
            glyph_rune_id=NC,
            metrics={"order": 3.0, "salience": 0.4},
        ),
    )
    scene = LumaSceneIR(
        scene_id="anim_heatmap_scene",
        source_frame_provenance=prov,
        patterns=tuple(),
        entities=entities,
        edges=tuple(),
        fields=NC,
        time_axis=NC,
        animation_plan=AnimationPlan(kind="none", steps=tuple()),
        semantic_map={},
        constraints={},
        seed=9,
        hash="",
    )
    scene_hash = LumaSceneIR.compute_hash(scene)
    return LumaSceneIR(
        scene_id=scene.scene_id,
        source_frame_provenance=scene.source_frame_provenance,
        patterns=scene.patterns,
        entities=scene.entities,
        edges=scene.edges,
        fields=scene.fields,
        time_axis=scene.time_axis,
        animation_plan=scene.animation_plan,
        semantic_map=scene.semantic_map,
        constraints=scene.constraints,
        seed=scene.seed,
        hash=scene_hash,
    )


def test_animation_plan_heatmap_is_stable():
    scene = _scene()
    a1 = render_animation_plan(scene)
    a2 = render_animation_plan(scene)
    assert a1.content_sha256 == a2.content_sha256

    plan = json.loads(a1.content)
    assert plan["modules"]["heatmap"]["enabled"] is True
    assert len(plan["modules"]["heatmap"]["cells"]) == 2
