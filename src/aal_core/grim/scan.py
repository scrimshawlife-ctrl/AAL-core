"""Manifest discovery and normalization for GRIM."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .model import RuneEdge, RuneRecord


_MANIFEST_PATTERNS = (
    "**/rune.manifest.json",
    "**/*rune*.manifest.json",
)


def discover_manifests(repo_root: Path) -> List[Path]:
    paths: List[Path] = []
    for pattern in _MANIFEST_PATTERNS:
        paths.extend(repo_root.rglob(pattern))
    abx_dir = repo_root / "abx_runes"
    if abx_dir.exists():
        paths.extend(repo_root.rglob("abx_runes/**/manifest.json"))
    deduped = sorted({p.resolve() for p in paths})
    return deduped


def scan_repo(repo_root: Path, overlay_name: str) -> List[RuneRecord]:
    records: List[RuneRecord] = []
    for manifest_path in discover_manifests(repo_root):
        record = parse_manifest(manifest_path, overlay_name)
        if record:
            records.append(record)
    return records


def parse_manifest(path: Path, overlay_name: str) -> Optional[RuneRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rune_id = str(data.get("rune_id") or data.get("id") or "").strip()
    name = str(data.get("name") or "").strip()
    if not rune_id and name:
        rune_id = _derive_rune_id(name)
    if not rune_id:
        return None

    capabilities = _normalize_list_field(data.get("capabilities"))
    tags = _normalize_list_field(data.get("tags"))
    edges_out = _parse_edges(data.get("edges_out") or data.get("edges") or [])
    for edge in edges_out:
        edge.src_id = rune_id
    record = RuneRecord(
        rune_id=rune_id,
        name=name or rune_id,
        version=_normalize_optional(data.get("version")),
        description=_normalize_optional(data.get("description")),
        capabilities=capabilities,
        tags=tags,
        edges_out=edges_out,
        provenance=[{"path": str(path), "overlay": overlay_name}],
    )
    return record.normalized()


def _normalize_list_field(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return []


def _parse_edges(edges: Iterable[Dict[str, Any]]) -> List[RuneEdge]:
    parsed: List[RuneEdge] = []
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        dst = str(edge.get("dst_id") or edge.get("to") or "").strip()
        if not dst:
            continue
        kind = str(edge.get("kind") or "link")
        parsed.append(RuneEdge(src_id="", dst_id=dst, kind=kind))
    return parsed


def _normalize_optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _derive_rune_id(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return f"rune.{slug}" if slug else ""
