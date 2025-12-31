from abx_runes.yggdrasil.inputs_bundle import InputBundle
from abx_runes.yggdrasil.plan import build_execution_plan
from abx_runes.yggdrasil.linkgen import evidence_port_name
from abx_runes.yggdrasil.schema import (
    Lane,
    NodeKind,
    PlanOptions,
    PortSpec,
    ProvenanceSpec,
    Realm,
    RuneLink,
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


def test_shadow_forecast_bridge_requires_evidence_bundle_in_input_bundle():
    """
    Shadow→Forecast bridge requires explicit_shadow_forecast_bridge:evidence_bundle
    in the InputBundle. If missing, the forecast node is pruned as not_computable.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(id="hel.det", kind=NodeKind.RUNE, realm=Realm.HEL, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="asg.pred", kind=NodeKind.RUNE, realm=Realm.ASGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("hel.det",)),
        ),
        links=(
            RuneLink(
                id="link0",
                from_node="root",
                to_node="hel.det",
                allowed_lanes=("neutral->shadow",),
            ),
            RuneLink(
                id="link1",
                from_node="hel.det",
                to_node="asg.pred",
                allowed_lanes=("shadow->forecast",),
                evidence_required=("EXPLICIT_SHADOW_FORECAST_BRIDGE",),
                required_evidence_ports=(PortSpec(name=evidence_port_name("hel.det", "asg.pred"), dtype="evidence_bundle", required=True),),
            ),
        ),
    )

    # Missing evidence bundle => prune forecast node
    plan = build_execution_plan(m, PlanOptions(input_bundle=InputBundle(present={})))
    assert "asg.pred" in plan.pruned_node_ids
    nc = plan.planner_trace.get("not_computable", {})
    assert "asg.pred" in nc
    assert "missing_bridge_evidence:" in nc["asg.pred"]

    # Present evidence bundle => keep forecast node
    plan2 = build_execution_plan(
        m,
        PlanOptions(input_bundle=InputBundle(present={evidence_port_name("hel.det", "asg.pred"): "evidence_bundle"})),
    )
    assert "asg.pred" in plan2.ordered_node_ids
    assert "asg.pred" not in plan2.pruned_node_ids


def test_bridge_evidence_dtype_mismatch_prunes_node():
    """
    If the evidence port dtype doesn't match exactly, the node is pruned.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(id="hel.det", kind=NodeKind.RUNE, realm=Realm.HEL, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="asg.pred", kind=NodeKind.RUNE, realm=Realm.ASGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("hel.det",)),
        ),
        links=(
            RuneLink(
                id="link0",
                from_node="root",
                to_node="hel.det",
                allowed_lanes=("neutral->shadow",),
            ),
            RuneLink(
                id="link1",
                from_node="hel.det",
                to_node="asg.pred",
                allowed_lanes=("shadow->forecast",),
                evidence_required=("EXPLICIT_SHADOW_FORECAST_BRIDGE",),
                required_evidence_ports=(PortSpec(name=evidence_port_name("hel.det", "asg.pred"), dtype="evidence_bundle", required=True),),
            ),
        ),
    )

    # Wrong dtype => prune
    plan = build_execution_plan(m, PlanOptions(input_bundle=InputBundle(present={evidence_port_name("hel.det", "asg.pred"): "wrong_dtype"})))
    assert "asg.pred" in plan.pruned_node_ids
    nc = plan.planner_trace.get("not_computable", {})
    assert "asg.pred" in nc
    assert "missing_bridge_evidence:" in nc["asg.pred"]


def test_no_input_bundle_means_no_bridge_evidence_check():
    """
    If no InputBundle is provided, no bridge evidence checking occurs.
    """
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(id="hel.det", kind=NodeKind.RUNE, realm=Realm.HEL, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="asg.pred", kind=NodeKind.RUNE, realm=Realm.ASGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("hel.det",)),
        ),
        links=(
            RuneLink(
                id="link0",
                from_node="root",
                to_node="hel.det",
                allowed_lanes=("neutral->shadow",),
            ),
            RuneLink(
                id="link1",
                from_node="hel.det",
                to_node="asg.pred",
                allowed_lanes=("shadow->forecast",),
                evidence_required=("EXPLICIT_SHADOW_FORECAST_BRIDGE",),
                required_evidence_ports=(PortSpec(name=evidence_port_name("hel.det", "asg.pred"), dtype="evidence_bundle", required=True),),
            ),
        ),
    )

    # No bundle => no checking, forecast node stays
    plan = build_execution_plan(m, PlanOptions(input_bundle=None))
    assert "asg.pred" in plan.ordered_node_ids
    assert "asg.pred" not in plan.pruned_node_ids
