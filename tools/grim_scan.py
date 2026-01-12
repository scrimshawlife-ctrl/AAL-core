#!/usr/bin/env python3
"""
GRIM scan tool for Abraxas overlays.

Purpose:
  - Discover rune manifests in this repo deterministically
  - Produce artifacts for debugging orphaned runes + dangling edges
  - Output an overlay delta that AAL-core GRIM can merge later

Definitions:
  - Orphan rune: rune exists but has no inbound/outbound edges (NOT an error)
  - Dangling edge: edge points to a dst_id that cannot be resolved in discovered rune_ids (ERROR)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------
# Models (kept local on purpose)
# ---------------------------


def _uniq_sorted(xs: List[str]) -> List[str]:
    return sorted({x.strip() for x in xs if isinstance(x, str) and x.strip()})


@dataclass(frozen=True)
class RuneEdge:
    src_id: str
    dst_id: str
    kind: str = "depends_on"
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuneRecord:
    rune_id: str
    name: str
    version: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    overlay: str = "abraxas"
    source_path: str = ""
    status: str = "active"
    replaced_by: Optional[str] = None
    edges_out: List[RuneEdge] = field(default_factory=list)

    def normalized(self) -> "RuneRecord":
        self.capabilities = _uniq_sorted(self.capabilities)
        self.tags = _uniq_sorted(self.tags)
        self.edges_out = sorted(self.edges_out, key=lambda e: (e.src_id, e.dst_id, e.kind))
        return self


# ---------------------------
# Discovery
# ---------------------------

MANIFEST_GLOBS = (
    "**/rune.manifest.json",
    "**/*rune*.manifest.json",
    "abx_runes/**/manifest.json",
    "registry/**/rune.manifest.json",
    "schemas/**/rune.manifest.json",
)


def _relpath(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except Exception:
        return str(p)


def _derive_rune_id(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    if not cleaned.startswith("rune."):
        cleaned = "rune." + cleaned
    return cleaned


def _parse_edges(raw_edges: Any, fallback_src: str) -> List[RuneEdge]:
    edges: List[RuneEdge] = []
    if not isinstance(raw_edges, list):
        return edges
    for e in raw_edges:
        if not isinstance(e, dict):
            continue
        src = str(e.get("src_id") or fallback_src).strip()
        dst = str(e.get("dst_id") or e.get("to") or "").strip()
        if not dst:
            continue
        kind = str(e.get("kind") or e.get("type") or "depends_on").strip()
        meta = e.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {"_meta": meta}
        edges.append(RuneEdge(src_id=src, dst_id=dst, kind=kind, meta=meta))
    return edges


def manifest_to_record(data: Dict[str, Any], *, source_path: str, overlay: str) -> Optional[RuneRecord]:
    rune_id = str(data.get("rune_id") or data.get("id") or "").strip()
    name = str(data.get("name") or "").strip()
    version = str(data.get("version") or data.get("semver") or "0.0.0").strip()
    description = str(data.get("description") or data.get("desc") or "").strip()

    if not rune_id:
        if not name:
            return None
        rune_id = _derive_rune_id(name)

    caps = data.get("capabilities") or data.get("caps") or []
    if isinstance(caps, str):
        caps = [caps]
    if not isinstance(caps, list):
        caps = [str(caps)]

    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        tags = [str(tags)]

    status = str(data.get("status") or "active").strip()
    replaced_by = data.get("replaced_by")
    if replaced_by is not None:
        replaced_by = str(replaced_by).strip() or None

    raw_edges = data.get("edges_out") or data.get("edges") or []
    edges_out = _parse_edges(raw_edges, fallback_src=rune_id)

    return RuneRecord(
        rune_id=rune_id,
        name=name or rune_id,
        version=version,
        description=description,
        capabilities=[str(x) for x in caps],
        tags=[str(x) for x in tags],
        overlay=overlay,
        source_path=source_path,
        status=status,
        replaced_by=replaced_by,
        edges_out=edges_out,
    ).normalized()


def iter_manifest_files(repo_root: Path) -> List[Path]:
    hits: Set[Path] = set()
    for pat in MANIFEST_GLOBS:
        for p in repo_root.glob(pat):
            if p.is_file():
                hits.add(p.resolve())
    return sorted(hits)


def scan(repo_root: Path, overlay: str) -> List[RuneRecord]:
    recs: List[RuneRecord] = []
    for mf in iter_manifest_files(repo_root):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec = manifest_to_record(data, source_path=_relpath(mf, repo_root), overlay=overlay)
        if rec:
            recs.append(rec)
    return sorted(recs, key=lambda r: (r.rune_id, r.version, r.name))


# ---------------------------
# Validation
# ---------------------------


def build_edge_list(recs: List[RuneRecord]) -> List[RuneEdge]:
    edges: List[RuneEdge] = []
    for r in recs:
        edges.extend(r.edges_out)
    return sorted(edges, key=lambda e: (e.src_id, e.dst_id, e.kind))


def find_dangling_edges(recs: List[RuneRecord]) -> List[Dict[str, Any]]:
    known: Set[str] = {r.rune_id for r in recs}
    bad: List[Dict[str, Any]] = []
    for e in build_edge_list(recs):
        if e.dst_id not in known:
            bad.append(
                {
                    "src_id": e.src_id,
                    "dst_id": e.dst_id,
                    "kind": e.kind,
                    "meta": e.meta,
                    "reason": "missing_dst_rune_id",
                }
            )
    return bad


def find_orphans(recs: List[RuneRecord]) -> List[str]:
    inbound: Set[str] = set()
    outbound: Set[str] = set()
    for e in build_edge_list(recs):
        outbound.add(e.src_id)
        inbound.add(e.dst_id)
    orphans = [r.rune_id for r in recs if (r.rune_id not in inbound and r.rune_id not in outbound)]
    return sorted(orphans)


def make_reports(recs: List[RuneRecord]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    dangling = find_dangling_edges(recs)
    orphans = find_orphans(recs)

    validation_report = {
        "schema_version": "grim.validation_report.v1",
        "counts": {
            "runes": len(recs),
            "edges": len(build_edge_list(recs)),
            "dangling_edges": len(dangling),
            "orphan_runes": len(orphans),
        },
        "dangling_edges": dangling,
        "orphan_runes": orphans,
    }

    overlay_delta = {
        "schema_version": "grim.overlay_delta.v1",
        "overlay": (recs[0].overlay if recs else "abraxas"),
        "records": {
            r.rune_id: {
                "rune_id": r.rune_id,
                "name": r.name,
                "version": r.version,
                "description": r.description,
                "capabilities": r.capabilities,
                "tags": r.tags,
                "overlay": r.overlay,
                "source_path": r.source_path,
                "status": r.status,
                "replaced_by": r.replaced_by,
                "edges_out": [asdict(e) for e in r.edges_out],
            }
            for r in sorted(recs, key=lambda x: x.rune_id)
        },
    }
    return validation_report, overlay_delta


def write_json(obj: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------
# CLI
# ---------------------------


def main() -> int:
    ap = argparse.ArgumentParser(prog="grim_scan")
    ap.add_argument("--repo-root", default=".", help="Abraxas repo root")
    ap.add_argument("--overlay", default="abraxas", help="Overlay name label")
    ap.add_argument("--out-dir", default=".aal/grim", help="Output dir for artifacts")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    out_dir = (root / args.out_dir).resolve()

    recs = scan(root, overlay=args.overlay)
    validation_report, overlay_delta = make_reports(recs)

    write_json(overlay_delta, out_dir / "abx_grim.overlay_delta.json")
    write_json(validation_report, out_dir / "abx_grim.validation_report.json")

    # Exit code: dangling edges are graph poison
    return 2 if validation_report["counts"]["dangling_edges"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
