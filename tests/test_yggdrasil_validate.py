import pytest

from abx_runes.yggdrasil.schema import (
    Lane,
    NodeKind,
    ProvenanceSpec,
    Realm,
    RuneLink,
    YggdrasilManifest,
    YggdrasilNode,
)
from abx_runes.yggdrasil.validate import ValidationError, validate_manifest


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
            YggdrasilNode(id="shadow.det", kind=NodeKind.RUNE, realm=Realm.HEL, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="forecast.pred", kind=NodeKind.RUNE, realm=Realm.ASGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("shadow.det",)),
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
            YggdrasilNode(id="shadow.det", kind=NodeKind.RUNE, realm=Realm.HEL, lane=Lane.SHADOW, authority_level=50, parent="root", depends_on=("root",)),
            YggdrasilNode(id="forecast.pred", kind=NodeKind.RUNE, realm=Realm.ASGARD, lane=Lane.FORECAST, authority_level=50, parent="root", depends_on=("shadow.det",)),
        ),
        links=(
            RuneLink(id="link0", from_node="root", to_node="shadow.det", allowed_lanes=("neutral->shadow",)),
            RuneLink(id="link1", from_node="shadow.det", to_node="forecast.pred", allowed_lanes=("shadow->forecast",)),
        ),
    )
    validate_manifest(m)
