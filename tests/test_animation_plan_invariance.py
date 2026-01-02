import sys
from pathlib import Path

# Add src to path for imports (repo convention)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aal_core.modules.luma.contracts.enums import NotComputable, PatternKind
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance, sha256_hex
from aal_core.modules.luma.contracts.scene_ir import (
    AnimationPlan,
    LumaSceneIR,
    PatternInstance,
    SceneEdge,
    SceneEntity,
    TimeAxis,
)
from aal_core.modules.luma.renderers.animation_plan import render_animation_plan

NC = NotComputable.VALUE.value


def _scene() -> LumaSceneIR:
    frame_prov = SourceFrameProvenance(
        module="unit_test",
        utc="2026-01-02T00:00:00Z",
        payload_sha256="a" * 64,
        vendor_lock_sha256="b" * 64,
        manifest_sha256="c" * 64,
        abx_runes_used=tuple(),
        abx_runes_gate_state="CLEAR",
    )

    patterns = (
        PatternInstance(
            kind=PatternKind.TEMPORAL_BRAID,
            pattern_id="temporal_braid/v1",
            inputs_sha256=sha256_hex({"steps": ("t0", "t1")}),
            failure_mode="none",
            affordances=("timeline",),
        ),
    )

    entities = (
        SceneEntity(
            entity_id="motif:x",
            kind="motif",
            label="x",
            domain=NC,
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        SceneEntity(
            entity_id="motif:y",
            kind="motif",
            label="y",
            domain=NC,
            glyph_rune_id=NC,
            metrics={"order": 1.0},
        ),
    )

    edges = (
        SceneEdge(
            edge_id="edge:0:x->y",
            source_id="motif:x",
            target_id="motif:y",
            kind="resonance",
            domain=NC,
            resonance_magnitude=0.7,
            uncertainty=0.1,
        ),
    )

    time_axis = TimeAxis(kind="discrete", t0_utc="2025-12-01T00:00:00Z", steps=("t0", "t1"))
    animation_plan = AnimationPlan(
        kind="timeline",
        steps=(
            {"t": "t0", "motifs": ["x"]},
            {"t": "t1", "motifs": ["x", "y"]},
        ),
    )

    base = LumaSceneIR(
        scene_id="anim_scene",
        source_frame_provenance=frame_prov,
        patterns=patterns,
        entities=entities,
        edges=edges,
        fields=NC,
        time_axis=time_axis,
        animation_plan=animation_plan,
        semantic_map={},
        constraints={"halflife_seconds": 3600},
        seed=55,
        hash="",
    )
    h = LumaSceneIR.compute_hash(base)
    return LumaSceneIR(
        scene_id=base.scene_id,
        source_frame_provenance=base.source_frame_provenance,
        patterns=base.patterns,
        entities=base.entities,
        edges=base.edges,
        fields=base.fields,
        time_axis=base.time_axis,
        animation_plan=base.animation_plan,
        semantic_map=base.semantic_map,
        constraints=base.constraints,
        seed=base.seed,
        hash=h,
    )


def test_animation_plan_is_stable():
    a1 = render_animation_plan(_scene())
    a2 = render_animation_plan(_scene())
    assert a1.content_sha256 == a2.content_sha256
    assert a1.scene_hash == a2.scene_hash

