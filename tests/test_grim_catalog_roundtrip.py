from pathlib import Path

from aal_core.grim.catalog import load_catalog, save_catalog
from aal_core.grim.model import GrimCatalog, RuneEdge, RuneRecord


def test_grim_catalog_roundtrip(tmp_path: Path) -> None:
    catalog = GrimCatalog()
    record = RuneRecord(
        rune_id="rune.alpha",
        name="Alpha Rune",
        version="1.0",
        description="First rune",
        capabilities=["forecast", "align"],
        tags=["alpha", "core"],
        edges_out=[RuneEdge(src_id="rune.alpha", dst_id="rune.beta", kind="link")],
        governance_status="active",
        provenance=[{"path": "/tmp/alpha.json", "overlay": "test"}],
    )
    catalog.upsert(record, source="test")

    path = tmp_path / "grim.catalog.json"
    save_catalog(catalog, path)
    loaded = load_catalog(path)

    assert loaded.to_dict() == catalog.to_dict()
