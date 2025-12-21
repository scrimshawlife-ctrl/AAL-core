#!/usr/bin/env python3
"""
AAL-core ABX-Runes Vendor Builder + Lock Verifier
=================================================

What it does (aal-core repo):
- Imports an ABX-Runes export bundle (dist/abx-runes/<version>/...) into
  src/aal_core/vendor/abx_runes/ with an atomic swap.
- Verifies export integrity via export_provenance.json + sha256 hashes.
- Writes/updates src/aal_core/vendor/abx_runes/LOCK.json (hash-locked).
- Generates a runtime accessor module (if missing):
    src/aal_core/runes/abx_runes.py
  exposing:
    list_runes(), get_rune(id), get_sigil_svg(id), verify_lock()
- Optional: verifies at runtime that the vendored asset hashes match LOCK.json.

No network calls. Stdlib only. Deterministic.

Run from aal-core repo root:
  python scripts/abx_runes_vendor_build.py --import /path/to/dist/abx-runes/v1.4
  python scripts/abx_runes_vendor_build.py --check

If your repo layout differs, set AAL_CORE_ROOT env var to the "src/aal_core" dir.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


IMPORTER_VERSION = "abx_runes_vendor_build@1"


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def compute_files(root: Path) -> List[Dict[str, str]]:
    files: List[Dict[str, str]] = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            files.append({"path": rel, "sha256": sha256_hex(p.read_bytes())})
    return files


def resolve_aal_core_src(repo_root: Path) -> Path:
    env = os.environ.get("AAL_CORE_ROOT")
    if env:
        p = Path(env).resolve()
        if not p.exists():
            raise SystemExit(f"AAL_CORE_ROOT does not exist: {p}")
        return p
    cand = repo_root / "src" / "aal_core"
    if cand.exists():
        return cand
    raise SystemExit("Could not locate src/aal_core. Set AAL_CORE_ROOT or run from aal-core repo root.")


def locate_export(src: Path) -> Path:
    """
    Accepts:
      - dist/abx-runes/<version> directory containing export_provenance.json
    """
    src = src.resolve()
    if (src / "export_provenance.json").exists():
        return src
    raise SystemExit(
        "Export not found. Pass the export directory containing export_provenance.json, e.g.\n"
        "  dist/abx-runes/v1.4"
    )


def verify_export(export_root: Path) -> Dict[str, Any]:
    prov_path = export_root / "export_provenance.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8"))

    mani = export_root / "sigils" / "manifest.json"
    if not mani.exists():
        raise SystemExit("Export missing sigils/manifest.json")

    if sha256_hex(mani.read_bytes()) != prov.get("manifest_sha256"):
        raise SystemExit("manifest_sha256 mismatch (export_provenance.json vs manifest.json)")

    # Verify every file hash listed in provenance
    files = prov.get("files", [])
    if not isinstance(files, list) or not files:
        raise SystemExit("export_provenance.json missing file list")

    for f in files:
        rel = f["path"]
        expected = f["sha256"]
        p = export_root / rel
        if not p.exists():
            raise SystemExit(f"Export missing file: {rel}")
        actual = sha256_hex(p.read_bytes())
        if actual != expected:
            raise SystemExit(f"Export hash mismatch: {rel}")

    # Sanity: registry.json + definitions
    if not (export_root / "registry.json").exists():
        raise SystemExit("Export missing registry.json")
    if not (export_root / "definitions").exists():
        raise SystemExit("Export missing definitions/")

    return prov


def ensure_runtime_accessor(aal_src: Path, *, write: bool) -> None:
    """
    Creates src/aal_core/runes/abx_runes.py if missing.
    """
    runes_dir = aal_src / "runes"
    runes_dir.mkdir(parents=True, exist_ok=True)
    accessor = runes_dir / "abx_runes.py"
    if accessor.exists():
        return

    text = """from __future__ import annotations
from pathlib import Path
import json, hashlib
from typing import Any, Dict, List

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "abx_runes"

def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def verify_lock() -> Dict[str, Any]:
    lock = VENDOR_ROOT / "LOCK.json"
    if not lock.exists():
        raise FileNotFoundError(f"Missing LOCK.json at {lock}")
    data = json.loads(lock.read_text(encoding="utf-8"))
    for f in data["files"]:
        p = VENDOR_ROOT / f["path"]
        if not p.exists():
            raise FileNotFoundError(f"Missing vendored file: {p}")
        if _sha256_hex(p.read_bytes()) != f["sha256"]:
            raise ValueError(f"Hash mismatch for {f['path']}")
    return {"ok": True, "abx_runes_version": data.get("abx_runes_version")}

def _registry() -> Dict[str, Any]:
    verify_lock()
    reg = VENDOR_ROOT / "registry.json"
    return json.loads(reg.read_text(encoding="utf-8"))

def list_runes() -> List[Dict[str, Any]]:
    return _registry()["runes"]

def get_rune(rune_id: str) -> Dict[str, Any]:
    for r in list_runes():
        if r["id"] == rune_id:
            return r
    raise KeyError(f"Unknown rune id: {rune_id}")

def get_sigil_svg(rune_id: str) -> str:
    r = get_rune(rune_id)
    fn = f'{r["id"]}_{r["short_name"]}.svg'
    p = VENDOR_ROOT / "sigils" / fn
    return p.read_text(encoding="utf-8")
"""
    if write:
        accessor.write_text(text, encoding="utf-8", newline="\n")


def import_export_into_vendor(aal_src: Path, export_root: Path, prov: Dict[str, Any], *, write: bool) -> Path:
    """
    Copies export_root into vendor dir with atomic swap and writes LOCK.json.
    """
    vendor = aal_src / "vendor" / "abx_runes"
    tmp = aal_src.parent / ".tmp_abx_runes_import"

    if tmp.exists():
        shutil.rmtree(tmp)

    if write:
        shutil.copytree(export_root, tmp)

        lock = {
            "abx_runes_version": prov.get("abx_runes_version") or export_root.name,
            "generator_version": IMPORTER_VERSION,
            "imported_at_utc": datetime.now(timezone.utc).isoformat(),
            "manifest_sha256": prov.get("manifest_sha256"),
            "files": compute_files(tmp),
            "source_hint": str(export_root),
            "source_commit": prov.get("source_commit"),
        }
        (tmp / "LOCK.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

        if vendor.exists():
            shutil.rmtree(vendor)
        vendor.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp), str(vendor))
    return vendor


def check_vendor(aal_src: Path) -> None:
    vendor = aal_src / "vendor" / "abx_runes"
    lock = vendor / "LOCK.json"
    if not lock.exists():
        raise SystemExit(f"Missing vendor lock: {lock}")

    data = json.loads(lock.read_text(encoding="utf-8"))
    for f in data.get("files", []):
        p = vendor / f["path"]
        if not p.exists():
            raise SystemExit(f"Missing vendored file: {f['path']}")
        if sha256_hex(p.read_bytes()) != f["sha256"]:
            raise SystemExit(f"Vendored hash mismatch: {f['path']}")

    # Sanity: access required files
    for rel in ("sigils/manifest.json", "registry.json"):
        if not (vendor / rel).exists():
            raise SystemExit(f"Vendored missing: {rel}")

    print("[OK] Vendor lock verified.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="import_path", default=None, help="Path to dist/abx-runes/<version> export directory")
    ap.add_argument("--write", action="store_true", help="Write changes to disk (used with --import).")
    ap.add_argument("--check", action="store_true", help="Verify current vendor lock and files.")
    args = ap.parse_args()

    repo_root = Path.cwd().resolve()
    aal_src = resolve_aal_core_src(repo_root)

    if args.check:
        check_vendor(aal_src)
        return 0

    if not args.import_path:
        raise SystemExit("Provide --import /path/to/dist/abx-runes/<version> (and usually --write).")

    export_root = locate_export(Path(args.import_path))
    prov = verify_export(export_root)

    # Ensure runtime accessor exists
    ensure_runtime_accessor(aal_src, write=args.write)

    # Import
    vendor = import_export_into_vendor(aal_src, export_root, prov, write=args.write)

    if args.write:
        print(f"[DONE] Imported ABX-Runes to: {vendor}")
        print("Next:")
        print("  python scripts/abx_runes_vendor_build.py --check")
    else:
        print("[DRYRUN] Verified export. Re-run with --write to import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
