import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aal_core.modules.luma.contracts.scene_ir import LumaEdge, LumaEntity, LumaSceneIR
from aal_core.modules.luma.renderers.svg_static import SvgRenderConfig, SvgStaticRenderer


def _scene() -> LumaSceneIR:
    return LumaSceneIR(
        scene_id="test_scene",
        seed=42,
        provenance={"source": "unit_test"},
        entities=[
            LumaEntity("m2", "motif", {"salience": 0.4}),
            LumaEntity("m1", "motif", {"salience": 0.7}),
        ],
        edges=[
            LumaEdge("m1", "m2", "resonance", 0.8, {}),
            LumaEdge("m2", "m1", "synch", 0.2, {}),
        ],
        patterns=[],
        semantic_map={},
        constraints={},
    )


def test_svg_bytes_hash_stable():
    r = SvgStaticRenderer()
    cfg = SvgRenderConfig(width=800, height=600)
    a1 = r.render(_scene(), cfg)
    a2 = r.render(_scene(), cfg)
    assert a1.bytes_sha256 == a2.bytes_sha256
    assert a1.scene_hash == a2.scene_hash


def test_scene_hash_stable_under_reordering():
    # same logical graph, different input order
    s1 = _scene()
    s2 = LumaSceneIR(
        scene_id="test_scene",
        seed=42,
        provenance={"source": "unit_test"},
        entities=list(reversed(s1.entities)),
        edges=list(reversed(s1.edges)),
        patterns=[],
        semantic_map={},
        constraints={},
    )
    assert s1.stable_hash() == s2.stable_hash()

