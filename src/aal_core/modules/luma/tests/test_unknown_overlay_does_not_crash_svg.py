import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.enums import NotComputable, PatternKind
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance
from aal_core.modules.luma.contracts.scene_ir import AnimationPlan, LumaSceneIR, PatternInstance, SceneEdge, SceneEntity
from aal_core.modules.luma.renderers.svg_static import render_svg

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
            entity_id="motif:a",
            kind="motif",
            label="A",
            domain="not_computable",
            glyph_rune_id=NC,
            metrics={"order": 0.0, "salience": 0.8},
        ),
        SceneEntity(
            entity_id="motif:b",
            kind="motif",
            label="B",
            domain="not_computable",
            glyph_rune_id=NC,
            metrics={"order": 1.0, "salience": 0.3},
        ),
    )
    edges = (
        SceneEdge(
            edge_id="edge:a->b",
            source_id="motif:a",
            target_id="motif:b",
            kind="resonance",
            domain="not_computable",
            resonance_magnitude=0.7,
            uncertainty=NC,
        ),
    )
    patterns = (
        PatternInstance(
            kind=PatternKind.MOTIF_GRAPH,
            pattern_id="totally_new_overlay/v1",
            inputs_sha256="0" * 64,
            failure_mode="none",
            affordances=tuple(),
        ),
    )
    scene = LumaSceneIR(
        scene_id="unknown_overlay_scene",
        source_frame_provenance=prov,
        patterns=patterns,
        entities=entities,
        edges=edges,
        fields=NC,
        time_axis=NC,
        animation_plan=AnimationPlan(kind="none", steps=tuple()),
        semantic_map={},
        constraints={},
        seed=2,
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


def test_unknown_overlay_falls_back_to_auto_view():
    artifact = render_svg(_scene())
    assert len(artifact.content) > 100
    assert "auto_view_fallback" in artifact.content
