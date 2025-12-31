from abx_runes.yggdrasil.schema import (
    Lane,
    NodeKind,
    PlanOptions,
    ProvenanceSpec,
    Realm,
    RuneLink,
    YggdrasilManifest,
    YggdrasilNode,
)
from abx_runes.yggdrasil.plan import build_execution_plan
from abx_runes.yggdrasil.render import render_tree_view, render_veins_view, render_plan


def main() -> None:
    prov = ProvenanceSpec(
        schema_version="yggdrasil-ir/0.1",
        manifest_hash="demo",
        created_at="2025-12-30T00:00:00Z",
        updated_at="2025-12-30T00:00:00Z",
        source_commit="local",
    )

    m = YggdrasilManifest(
        provenance=prov,
        nodes=(
            YggdrasilNode(
                id="root.seed",
                kind=NodeKind.ROOT_POLICY,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=100,
                parent=None,
            ),
            YggdrasilNode(
                id="kernel.registry",
                kind=NodeKind.KERNEL,
                realm=Realm.MIDGARD,
                lane=Lane.NEUTRAL,
                authority_level=90,
                parent="root.seed",
                depends_on=("root.seed",),
            ),
            YggdrasilNode(
                id="realm.hel",
                kind=NodeKind.REALM,
                realm=Realm.HEL,
                lane=Lane.SHADOW,
                authority_level=80,
                parent="kernel.registry",
            ),
            YggdrasilNode(
                id="realm.asgard",
                kind=NodeKind.REALM,
                realm=Realm.ASGARD,
                lane=Lane.FORECAST,
                authority_level=80,
                parent="kernel.registry",
            ),
        ),
        links=(),
    )

    print("TREE:")
    print(render_tree_view(m))
    print("\nVEINS:")
    print(render_veins_view(m))

    plan = build_execution_plan(m, PlanOptions())
    print("\nPLAN:")
    print(render_plan(plan))


if __name__ == "__main__":
    main()
