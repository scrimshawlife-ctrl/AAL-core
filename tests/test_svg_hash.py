import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aal_core.modules.luma.contracts.scene_ir import SceneEdge, SceneEntity, LumaSceneIR
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance
from aal_core.modules.luma.renderers.svg_static import SvgRenderConfig, SvgStaticRenderer


def _scene() -> LumaSceneIR:
    """Create a test scene using the current API."""
    NC = "not_computable"

    # Create source frame provenance
    provenance = SourceFrameProvenance(
        module="test_module",
        utc="2026-01-12T00:00:00Z",
        payload_sha256="abc123" * 10,  # 64-char hex
        vendor_lock_sha256="def456" * 10,
        manifest_sha256="789abc" * 10,
        abx_runes_used=(),
        abx_runes_gate_state="open",
    )

    # Create entities with all required fields
    entities = (
        SceneEntity(
            entity_id="m2",
            kind="motif",
            label="Motif 2",
            domain="test_domain",
            glyph_rune_id=NC,
            metrics={"salience": 0.4},
            attributes={},
        ),
        SceneEntity(
            entity_id="m1",
            kind="motif",
            label="Motif 1",
            domain="test_domain",
            glyph_rune_id=NC,
            metrics={"salience": 0.7},
            attributes={},
        ),
    )

    # Create edges with all required fields
    edges = (
        SceneEdge(
            edge_id="e1",
            source_id="m1",
            target_id="m2",
            kind="resonance",
            domain="test_domain",
            resonance_magnitude=0.8,
            uncertainty=0.0,
        ),
        SceneEdge(
            edge_id="e2",
            source_id="m2",
            target_id="m1",
            kind="synch",
            domain="test_domain",
            resonance_magnitude=0.2,
            uncertainty=0.0,
        ),
    )

    # Compute hash for the scene
    import hashlib
    scene_hash = hashlib.sha256(b"test_scene_42").hexdigest()[:16]

    return LumaSceneIR(
        scene_id="test_scene",
        source_frame_provenance=provenance,
        patterns=(),
        entities=entities,
        edges=edges,
        fields=NC,
        time_axis=NC,
        animation_plan=NC,
        semantic_map={},
        constraints={},
        seed=42,
        hash=scene_hash,
    )


def test_svg_bytes_hash_stable():
    r = SvgStaticRenderer()
    cfg = SvgRenderConfig(width=800, height=600)
    a1 = r.render(_scene(), cfg)
    a2 = r.render(_scene(), cfg)
    assert a1.bytes_sha256 == a2.bytes_sha256
    assert a1.scene_hash == a2.scene_hash


def test_scene_hash_stable_under_reordering():
    """Test that scene hash is stable regardless of entity/edge order."""
    # same logical graph, different input order
    s1 = _scene()

    # Create s2 with reversed entities and edges but same content
    s2 = LumaSceneIR(
        scene_id=s1.scene_id,
        source_frame_provenance=s1.source_frame_provenance,
        patterns=s1.patterns,
        entities=tuple(reversed(s1.entities)) if isinstance(s1.entities, tuple) else s1.entities,
        edges=tuple(reversed(s1.edges)) if isinstance(s1.edges, tuple) else s1.edges,
        fields=s1.fields,
        time_axis=s1.time_axis,
        animation_plan=s1.animation_plan,
        semantic_map=s1.semantic_map,
        constraints=s1.constraints,
        seed=s1.seed,
        hash=s1.hash,
    )

    # Hash should be stable because canonical dict sorts entities/edges by ID
    h1 = s1.to_canonical_dict()
    h2 = s2.to_canonical_dict()

    # The canonical representations should be identical
    assert h1 == h2

