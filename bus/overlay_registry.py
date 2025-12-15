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

        if use_cache and name in _CACHE:
            cached_dir, cached_mf, cached_hash = _CACHE[name]
            if cached_hash == manifest_hash:
                overlays[name] = (cached_dir, cached_mf, cached_hash)
                continue

        capabilities = raw_data.get("capabilities", [])
        if not isinstance(capabilities, list) or not all(isinstance(x, str) for x in capabilities):
            raise ValueError("manifest.capabilities must be a list[str]")

        # NEW: op_policy (trusted allowlist + required caps)
        op_policy = raw_data.get("op_policy", {})
        if not isinstance(op_policy, dict):
            raise ValueError("manifest.op_policy must be an object/dict")

        # normalize: op -> list[str]
        norm_op_policy: Dict[str, list[str]] = {}
        for op, caps in op_policy.items():
            if not isinstance(op, str):
                raise ValueError("manifest.op_policy keys must be strings")
            if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
                raise ValueError(f"manifest.op_policy['{op}'] must be list[str]")
            norm_op_policy[op] = list(caps)

        mf = OverlayManifest(
            name=name,
            version=str(raw_data.get("version", "unknown")),
            status=str(raw_data.get("status", "unknown")),
            phases=_as_phase_list(raw_data.get("phases", [])),
            entrypoint=str(raw_data.get("entrypoint", "")).strip(),
            capabilities=list(capabilities),
            op_policy=norm_op_policy,
            timeout_ms=int(raw_data.get("timeout_ms", 2500)),
        )

        if not mf.entrypoint:
            raise ValueError(f"Missing entrypoint in manifest: {manifest_path}")

        _CACHE[name] = (overlay_dir, mf, manifest_hash)
        overlays[name] = (overlay_dir, mf, manifest_hash)

    # prune deleted overlays from cache
    cached_names = set(_CACHE.keys())
    current_names = set(overlays.keys())
    for dead in cached_names - current_names:
        del _CACHE[dead]

    return overlays
