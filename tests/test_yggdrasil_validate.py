import pytest

from aal_core.yggdrasil.schema import (
    Lane, NodeKind, PromotionState, ProvenanceSpec, Realm,
    YggdrasilManifest, YggdrasilNode, RuneLink
)
from aal_core.yggdrasil.validate import validate_manifest, ValidationError


def _prov():
    return ProvenanceSpec(
        schema_version="yggdrasil-ir/0.1",
        manifest_hash="x",
        created_at="t",
        updated_at="t",
        source_commit="c",
    )


def test_rejects_multiple_roots():
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="r1", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(id="r2", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
        ),
        links=(),
    )
    with pytest.raises(ValidationError):
        validate_manifest(m)


def test_blocks_shadow_to_forecast_without_link():
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(id="shadow.det", kind=NodeKind.RUNE, realm=Realm.MIDGARD, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="forecast.pred", kind=NodeKind.RUNE, realm=Realm.MIDGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("shadow.det",)),
        ),
        links=(),
    )
    with pytest.raises(ValidationError):
        validate_manifest(m)


def test_allows_shadow_to_forecast_only_if_link_explicit():
    m = YggdrasilManifest(
        provenance=_prov(),
        nodes=(
            YggdrasilNode(id="root", kind=NodeKind.ROOT_POLICY, realm=Realm.MIDGARD, lane=Lane.NEUTRAL, authority_level=100, parent=None),
            YggdrasilNode(id="shadow.det", kind=NodeKind.RUNE, realm=Realm.MIDGARD, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="forecast.pred", kind=NodeKind.RUNE, realm=Realm.MIDGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("shadow.det",)),
        ),
        links=(
            RuneLink(
                id="link1",
                from_node="shadow.det",
                to_node="forecast.pred",
                allowed_lanes=("shadow->forecast",),
                data_class="feature",
                determinism_rule="stable_sort_by_id",
                failure_mode="not_computable",
                evidence_required=(),
            ),
        ),
    )
    validate_manifest(m)
