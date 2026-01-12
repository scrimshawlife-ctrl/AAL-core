"""Catalog persistence utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .model import GrimCatalog


DEFAULT_CATALOG_RELATIVE = Path(".aal/grim/abx_grim.catalog.json")


def default_catalog_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_CATALOG_RELATIVE


def load_catalog(path: Path) -> GrimCatalog:
    if not path.exists():
        return GrimCatalog()
    data = json.loads(path.read_text(encoding="utf-8"))
    return GrimCatalog.from_dict(data)


def save_catalog(catalog: GrimCatalog, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = catalog.to_dict()
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def default_report_path(catalog_path: Path) -> Path:
    return catalog_path.with_name("abx_grim.validation_report.json")
