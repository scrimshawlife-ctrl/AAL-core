"""GRIM CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import default_catalog_path, default_report_path, load_catalog, save_catalog
from .scan import scan_repo
from .validate import validate_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GRIM rune catalog builder")
    parser.add_argument("--repo-root", default=".", help="Repository root to scan")
    parser.add_argument("--overlay-name", default="aal_core", help="Overlay name for provenance")
    parser.add_argument("--catalog", default=None, help="Catalog path override")
    parser.add_argument("--report", default=None, help="Validation report path override")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    catalog_path = Path(args.catalog) if args.catalog else default_catalog_path(repo_root)
    report_path = Path(args.report) if args.report else default_report_path(catalog_path)

    catalog = load_catalog(catalog_path)
    for record in scan_repo(repo_root, args.overlay_name):
        catalog.upsert(record, source=f"scan:{args.overlay_name}")
    save_catalog(catalog, catalog_path)

    report = validate_catalog(catalog)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    return 2 if report["summary"]["has_dangling_edges"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
