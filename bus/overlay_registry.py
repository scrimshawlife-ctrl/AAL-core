from __future__ import annotations
from pathlib import Path
import json
from typing import Dict

from .types import OverlayManifest, Phase

def _as_phase_list(raw) -> list[Phase]:
    phases = []
    for p in raw:
        if p not in ("OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"):
            raise ValueError(f"Invalid phase in manifest: {p}")
        phases.append(p)  # type: ignore
    return phases

def load_overlays(overlays_dir: Path) -> Dict[str, tuple[Path, OverlayManifest]]:
    overlays: Dict[str, tuple[Path, OverlayManifest]] = {}
    if not overlays_dir.exists():
        return overlays

    for overlay_dir in overlays_dir.iterdir():
        if not overlay_dir.is_dir():
            continue
        manifest_path = overlay_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        mf = OverlayManifest(
            name=str(data["name"]),
            version=str(data.get("version", "unknown")),
            status=str(data.get("status", "unknown")),
            phases=_as_phase_list(data.get("phases", [])),
            entrypoint=str(data.get("entrypoint", "")).strip(),
            timeout_ms=int(data.get("timeout_ms", 2500)),
        )

        if not mf.entrypoint:
            raise ValueError(f"Missing entrypoint in manifest: {manifest_path}")

        overlays[mf.name] = (overlay_dir, mf)

    return overlays
