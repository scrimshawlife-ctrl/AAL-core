import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.enums import NotComputable
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance
from aal_core.modules.luma.contracts.scene_ir import AnimationPlan, LumaSceneIR, SceneEdge, SceneEntity
from aal_core.modules.luma.ideation.auto_lens import AutoLens, AutoLensConfig

NC = NotComputable.VALUE.value


def _scene(pair_count: int) -> LumaSceneIR:
    prov = SourceFrameProvenance(
        module="test.luma",
        utc="2026-01-02T00:00:00Z",
        payload_sha256="0" * 64,
        vendor_lock_sha256="1" * 64,
        manifest_sha256="2" * 64,
        abx_runes_used=tuple(),
        abx_runes_gate_state="CLEAR",
    )
    domains = [f"domain:{i}" for i in range(4 + pair_count)]
    entities = tuple(
        SceneEntity(
            entity_id=dom,
            kind="domain",
            label=dom.split("domain:", 1)[-1],
            domain=dom.split("domain:", 1)[-1],
            glyph_rune_id=NC,
            metrics={"order": float(i)},
        )
        for i, dom in enumerate(domains)
    )
    pairs = [(domains[i], domains[i + 1]) for i in range(pair_count)]
    edges = tuple(
        SceneEdge(
            edge_id=f"flow:{i}:{s}->{t}",
            source_id=s,
            target_id=t,
            kind="transfer",
            domain=s.replace("domain:", ""),
            resonance_magnitude=0.6,
            uncertainty=NC,
        )
        for i, (s, t) in enumerate(pairs)
    )
    scene = LumaSceneIR(
        scene_id=f"pairs_{pair_count}",
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


def test_flow_density_heuristic():
    lens = AutoLens()
    cfg = AutoLensConfig(sankey_max_pairs=8)

    p_low = lens.plan(_scene(2), cfg)
    assert p_low.view_id == "auto.flow_v0"
    assert p_low.layout["preferred_flow_view"] == "sankey"

    p_high = lens.plan(_scene(9), cfg)
    assert p_high.view_id == "auto.flow_v0"
    assert p_high.layout["preferred_flow_view"] == "chord"
