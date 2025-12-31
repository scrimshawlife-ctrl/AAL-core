from __future__ import annotations

from abx_runes.yggdrasil.inputs_bundle import InputBundle
from abx_runes.yggdrasil.plan import build_execution_plan
from abx_runes.yggdrasil.render import render_plan
from abx_runes.yggdrasil.schema import (
    Lane,
    NodeKind,
    PlanOptions,
    PortSpec,
    ProvenanceSpec,
    Realm,
    YggdrasilManifest,
    YggdrasilNode,
)


def _prov():
    return ProvenanceSpec(
        schema_version="yggdrasil-ir/0.1",
        manifest_hash="x",
        created_at="t",
        updated_at="t",
        source_commit="c",
    )


def test_missing_required_input_prunes_node_and_dependents():
    """
    Node with required input that's missing from bundle gets pruned as not_computable.
    Nodes depending on it also get pruned (closure propagation).
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(
                id="a",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("root",),
                inputs=(PortSpec(name="news_feed", dtype="jsonl", required=True),),
            ),
            YggdrasilNode(
                id="b",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("a",),
            ),
        ),
        links=(),
    )

    # Missing news_feed input
    bundle = InputBundle(present={})
    plan = build_execution_plan(m, PlanOptions(input_bundle=bundle))

    # Node 'a' should be pruned as not_computable
    assert "a" in plan.pruned_node_ids

    # Node 'b' should be pruned (closure: depends on pruned 'a')
    assert "b" in plan.pruned_node_ids

    # Check not_computable reason is recorded
    nc = plan.planner_trace.get("not_computable", {})
    assert "a" in nc
    assert "missing_required_inputs:news_feed" in nc["a"]

    # Node 'b' was pruned by closure, not by missing inputs
    assert "b" not in nc


def test_present_input_allows_node_to_run():
    """
    Node with required input that IS present in bundle stays in plan.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(
                id="a",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("root",),
                inputs=(PortSpec(name="news_feed", dtype="jsonl", required=True),),
            ),
        ),
        links=(),
    )

    # news_feed is present with correct dtype
    bundle = InputBundle(present={"news_feed": "jsonl"})
    plan = build_execution_plan(m, PlanOptions(input_bundle=bundle))

    # Node 'a' should NOT be pruned
    assert "a" in plan.ordered_node_ids
    assert "a" not in plan.pruned_node_ids


def test_dtype_mismatch_prunes_node():
    """
    Input present but with wrong dtype → node gets pruned.
    Exact string matching enforced.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(
                id="a",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("root",),
                inputs=(PortSpec(name="news_feed", dtype="jsonl", required=True),),
            ),
        ),
        links=(),
    )

    # news_feed present but with WRONG dtype ("json" != "jsonl")
    bundle = InputBundle(present={"news_feed": "json"})
    plan = build_execution_plan(m, PlanOptions(input_bundle=bundle))

    # Node 'a' should be pruned (dtype mismatch)
    assert "a" in plan.pruned_node_ids
    nc = plan.planner_trace.get("not_computable", {})
    assert "a" in nc


def test_optional_input_missing_does_not_prune():
    """
    Optional inputs (required=False) don't cause pruning when missing.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(
                id="a",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("root",),
                inputs=(PortSpec(name="optional_config", dtype="json", required=False),),
            ),
        ),
        links=(),
    )

    # Bundle missing optional input
    bundle = InputBundle(present={})
    plan = build_execution_plan(m, PlanOptions(input_bundle=bundle))

    # Node 'a' should NOT be pruned (input is optional)
    assert "a" in plan.ordered_node_ids
    assert "a" not in plan.pruned_node_ids


def test_no_bundle_means_no_pruning():
    """
    If no InputBundle provided, no not-computable pruning occurs.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(
                id="a",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("root",),
                inputs=(PortSpec(name="news_feed", dtype="jsonl", required=True),),
            ),
        ),
        links=(),
    )

    # No bundle (input_bundle=None)
    plan = build_execution_plan(m, PlanOptions())

    # Node 'a' should NOT be pruned (no bundle means no input checking)
    assert "a" in plan.ordered_node_ids
    assert "a" not in plan.pruned_node_ids


def test_render_plan_shows_not_computable():
    """
    Rendered plan output includes NOT_COMPUTABLE section with reasons.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(
                id="a",
                kind=NodeKind.RUNE,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=50,
                parent="root",
                depends_on=("root",),
                inputs=(PortSpec(name="news_feed", dtype="jsonl", required=True),),
            ),
        ),
        links=(),
    )

    bundle = InputBundle(present={})
    plan = build_execution_plan(m, PlanOptions(input_bundle=bundle))
    rendered = render_plan(plan)

    # Should contain NOT_COMPUTABLE section
    assert "NOT_COMPUTABLE" in rendered
    assert "a: missing_required_inputs:news_feed" in rendered
