from aal_core.grim.model import GrimCatalog, RuneEdge, RuneRecord
from aal_core.grim.validate import validate_catalog


def test_grim_validate_dangling_edges() -> None:
    catalog = GrimCatalog()
    alpha = RuneRecord(
        rune_id="rune.alpha",
        name="Alpha",
        edges_out=[RuneEdge(src_id="rune.alpha", dst_id="rune.missing", kind="link")],
    )
    beta = RuneRecord(
        rune_id="rune.beta",
        name="Beta",
    )
    catalog.upsert(alpha, source="test")
    catalog.upsert(beta, source="test")

    report = validate_catalog(catalog)

    assert report["summary"]["dangling_edge_count"] == 1
    assert report["dangling_edges"][0]["dst_id"] == "rune.missing"
