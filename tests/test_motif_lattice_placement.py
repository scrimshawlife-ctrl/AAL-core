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
from aal_core.modules.luma.renderers.svg_static import render_svg

NC = NotComputable.VALUE.value


def _scene() -> LumaSceneIR:
    frame_prov = SourceFrameProvenance(
        module="unit_test",
        utc="2026-01-02T00:00:00Z",
        payload_sha256="0" * 64,
        vendor_lock_sha256="1" * 64,
        manifest_sha256="2" * 64,
        abx_runes_used=tuple(),
        abx_runes_gate_state="CLEAR",
    )

    patterns = (
        PatternInstance(
            kind=PatternKind.DOMAIN_LATTICE,
            pattern_id="domain_lattice/v1",
            inputs_sha256=sha256_hex({"domains": ("tech", "fin")}),
            failure_mode="none",
            affordances=("lattice",),
        ),
    )

    entities = (
        SceneEntity(
            entity_id="domain:tech",
            kind="domain",
            label="Tech/AI",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        SceneEntity(
            entity_id="domain:fin",
            kind="domain",
            label="Finance",
            domain="fin",
            glyph_rune_id=NC,
            metrics={"order": 1.0},
        ),
        SceneEntity(
            entity_id="subdomain:tech:llm",
            kind="subdomain",
            label="LLMs",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        SceneEntity(
            entity_id="subdomain:fin:mkt",
            kind="subdomain",
            label="Markets",
            domain="fin",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        # motifs snapped
        SceneEntity(
            entity_id="motif:a",
            kind="motif",
            label="a",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
            attributes={"domain_id": "domain:tech", "subdomain_id": "subdomain:tech:llm"},
        ),
        SceneEntity(
            entity_id="motif:b",
            kind="motif",
            label="b",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"order": 1.0},
            attributes={"domain_id": "domain:tech", "subdomain_id": "subdomain:tech:llm"},
        ),
        SceneEntity(
            entity_id="motif:c",
            kind="motif",
            label="c",
            domain="fin",
            glyph_rune_id=NC,
            metrics={"order": 2.0},
            attributes={"domain_id": "domain:fin", "subdomain_id": "subdomain:fin:mkt"},
        ),
    )

    edges = (
        SceneEdge(
            edge_id="edge:0:a->b",
            source_id="motif:a",
            target_id="motif:b",
            kind="resonance",
            domain="tech",
            resonance_magnitude=0.8,
            uncertainty=0.1,
        ),
        SceneEdge(
            edge_id="edge:1:a->c",
            source_id="motif:a",
            target_id="motif:c",
            kind="synch",
            domain="tech",
            resonance_magnitude=0.5,
            uncertainty=0.2,
        ),
    )

    base = LumaSceneIR(
        scene_id="motif_snap_scene",
        source_frame_provenance=frame_prov,
        patterns=patterns,
        entities=entities,
        edges=edges,
        fields=NC,
        time_axis=NC,
        animation_plan=AnimationPlan(kind="none", steps=tuple()),
        semantic_map={},
        constraints={},
        seed=101,
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


def test_motif_snap_svg_is_stable():
    a1 = render_svg(_scene())
    a2 = render_svg(_scene())
    assert a1.content_sha256 == a2.content_sha256

