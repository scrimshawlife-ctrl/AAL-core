from aal_core.yggdrasil.schema import (
    Lane, NodeKind, ProvenanceSpec, Realm,
    YggdrasilManifest, YggdrasilNode, PlanOptions
)
from aal_core.yggdrasil.plan import build_execution_plan


def _prov():
    return ProvenanceSpec(
        schema_version="yggdrasil-ir/0.1",
        manifest_hash="x",
        created_at="t",
        updated_at="t",
        source_commit="c",
    )


def test_plan_is_deterministic_under_input_order_variation():
    # same graph, nodes shuffled
    nodes_a = (
        YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
        YggdrasilNode(id="b", kind=NodeKind.RUNE, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=50, parent="root", depends_on=("a",)),
        YggdrasilNode(id="a", kind=NodeKind.RUNE, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=50, parent="root", depends_on=("root",)),
    )
    nodes_b = (nodes_a[2], nodes_a[0], nodes_a[1])

    m1 = YggdrasilManifest(provenance=_prov(), nodes=nodes_a, links=())
    m2 = YggdrasilManifest(provenance=_prov(), nodes=nodes_b, links=())

    p1 = build_execution_plan(m1, PlanOptions())
    p2 = build_execution_plan(m2, PlanOptions())

    assert p1.ordered_node_ids == p2.ordered_node_ids
