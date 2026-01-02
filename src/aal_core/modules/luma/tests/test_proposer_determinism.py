import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.enums import NotComputable
from aal_core.modules.luma.contracts.provenance import SourceFrameProvenance
from aal_core.modules.luma.contracts.scene_ir import (
    AnimationPlan,
    LumaSceneIR,
    SceneEdge,
    SceneEntity,
    TimeAxis,
)
from aal_core.modules.luma.ideation.proposer import PatternProposer, ProposerConfig

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
            entity_id="domain:geo",
            kind="domain",
            label="Geopolitics",
            domain="geo",
            glyph_rune_id=NC,
            metrics={"order": 0.0},
        ),
        SceneEntity(
            entity_id="domain:tech",
            kind="domain",
            label="Tech/AI",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"order": 1.0},
        ),
        SceneEntity(
            entity_id="motif:a",
            kind="motif",
            label="Alignment Drift",
            domain="geo",
            glyph_rune_id=NC,
            metrics={"salience": 0.9, "order": 2.0},
        ),
        SceneEntity(
            entity_id="motif:b",
            kind="motif",
            label="Compute Acceleration",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"salience": 0.4, "order": 3.0},
        ),
        SceneEntity(
            entity_id="motif:c",
            kind="motif",
            label="Policy Shock",
            domain="geo",
            glyph_rune_id=NC,
            metrics={"salience": 0.7, "order": 4.0},
        ),
        SceneEntity(
            entity_id="motif:d",
            kind="motif",
            label="Model Shift",
            domain="tech",
            glyph_rune_id=NC,
            metrics={"salience": 0.5, "order": 5.0},
        ),
    )
    edges = (
        SceneEdge(
            edge_id="flow:0:geo->tech",
            source_id="domain:geo",
            target_id="domain:tech",
            kind="transfer",
            domain="geo",
            resonance_magnitude=0.8,
            uncertainty=0.1,
        ),
        SceneEdge(
            edge_id="edge:motif:a->motif:b",
            source_id="motif:a",
            target_id="motif:b",
            kind="resonance",
            domain="geo",
            resonance_magnitude=0.7,
            uncertainty=0.2,
        ),
    )
    time_axis = TimeAxis(
        kind="discrete",
        t0_utc="2026-01-02T00:00:00Z",
        steps=("2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"),
    )
    scene = LumaSceneIR(
        scene_id="proposal_scene",
        source_frame_provenance=prov,
        patterns=tuple(),
        entities=entities,
        edges=edges,
        fields=NC,
        time_axis=time_axis,
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


def test_proposer_is_deterministic():
    proposer = PatternProposer()
    cfg = ProposerConfig(max_proposals=3)
    baseline = ["domain_lattice", "sankey_transfer", "temporal_braid", "motif_graph"]

    a = proposer.propose(_scene(), baseline, cfg)
    b = proposer.propose(_scene(), baseline, cfg)
    assert [x.proposal_id for x in a] == [x.proposal_id for x in b]
    assert [x.pattern_spec for x in a] == [x.pattern_spec for x in b]
