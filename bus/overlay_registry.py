from __future__ import annotations
from pathlib import Path
import json
import hashlib
from typing import Dict, Tuple

from .types import OverlayManifest, Phase

def _as_phase_list(raw) -> list[Phase]:
    phases = []
    for p in raw:
        if p not in ("OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"):
            raise ValueError(f"Invalid phase in manifest: {p}")
        phases.append(p)  # type: ignore
    return phases

def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _hash_manifest(data: dict) -> str:
    raw = _canonical_json(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

# Simple in-memory cache
_CACHE: Dict[str, Tuple[Path, OverlayManifest, str]] = {}

def load_overlays(overlays_dir: Path, use_cache: bool = True) -> Dict[str, Tuple[Path, OverlayManifest, str]]:
    overlays: Dict[str, Tuple[Path, OverlayManifest, str]] = {}

    if not overlays_dir.exists():
        _CACHE.clear()
        return overlays

    for overlay_dir in overlays_dir.iterdir():
        if not overlay_dir.is_dir():
            continue

        manifest_path = overlay_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        raw_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_hash = _hash_manifest(raw_data)

        name = str(raw_data["name"])

        # Cache hit
        if use_cache and name in _CACHE:
            cached_dir, cached_mf, cached_hash = _CACHE[name]
            if cached_hash == manifest_hash:
                overlays[name] = (cached_dir, cached_mf, cached_hash)
                continue

        # Cache miss or changed manifest
        mf = OverlayManifest(
            name=name,
            version=str(raw_data.get("version", "unknown")),
            status=str(raw_data.get("status", "unknown")),
            phases=_as_phase_list(raw_data.get("phases", [])),
            entrypoint=str(raw_data.get("entrypoint", "")).strip(),
            timeout_ms=int(raw_data.get("timeout_ms", 2500)),
        )

        if not mf.entrypoint:
            raise ValueError(f"Missing entrypoint in manifest: {manifest_path}")

        _CACHE[name] = (overlay_dir, mf, manifest_hash)
        overlays[name] = (overlay_dir, mf, manifest_hash)

    # Remove deleted overlays from cache
    cached_names = set(_CACHE.keys())
    current_names = set(overlays.keys())
    for dead in cached_names - current_names:
        del _CACHE[dead]

    return overlays
