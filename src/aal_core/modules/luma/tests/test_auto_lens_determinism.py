import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.enums import NotComputable
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance
from aal_core.modules.luma.contracts.scene_ir import AnimationPlan, LumaSceneIR, SceneEdge, SceneEntity
from aal_core.modules.luma.ideation.auto_lens import AutoLens, AutoLensConfig

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
            entity_id="domain:a",
            kind="domain",
            label="A",
            domain="a",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        SceneEntity(
            entity_id="domain:b",
            kind="domain",
            label="B",
            domain="b",
            glyph_rune_id=NC,
            metrics={"order": 1.0},
        ),
        SceneEntity(
            entity_id="motif:m1",
            kind="motif",
            label="M1",
            domain="a",
            glyph_rune_id=NC,
            metrics={"order": 2.0, "salience": 0.9},
        ),
        SceneEntity(
            entity_id="motif:m2",
            kind="motif",
            label="M2",
            domain="b",
            glyph_rune_id=NC,
            metrics={"order": 3.0, "salience": 0.4},
        ),
    )
    edges = (
        SceneEdge(
            edge_id="flow:0:a->b",
            source_id="domain:a",
            target_id="domain:b",
            kind="transfer",
            domain="a",
            resonance_magnitude=0.7,
            uncertainty=NC,
        ),
        SceneEdge(
            edge_id="edge:m1->m2",
            source_id="motif:m1",
            target_id="motif:m2",
            kind="resonance",
            domain="a",
            resonance_magnitude=0.6,
            uncertainty=NC,
        ),
    )
    scene = LumaSceneIR(
        scene_id="auto_scene",
        source_frame_provenance=prov,
        patterns=tuple(),
        entities=entities,
        edges=edges,
        fields=NC,
        time_axis=NC,
        animation_plan=AnimationPlan(kind="none", steps=tuple()),
        semantic_map={},
        constraints={},
        seed=1,
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


def test_auto_lens_plan_is_stable():
    lens = AutoLens()
    cfg = AutoLensConfig()
    p1 = lens.plan(_scene(), cfg)
    p2 = lens.plan(_scene(), cfg)
    assert p1.view_id == p2.view_id
    assert p1.layout == p2.layout
    assert p1.scores == p2.scores
