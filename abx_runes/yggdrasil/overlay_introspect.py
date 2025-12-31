from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .overlay_schema_validate import validate_overlay_manifest, OverlaySchemaError


@dataclass(frozen=True)
class OverlayRuneDecl:
    """
    A declared rune inside an overlay.
    We keep this intentionally tiny and JSON-first.
    """
    rune_id: str
    kind: str = "rune"
    depends_on: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()


def load_overlay_manifest_json(overlay_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Convention: overlay may provide one of:
      - manifest.json
      - overlay.json
      - yggdrasil.overlay.json

    Validates against yggdrasil-overlay/0.1 schema contract.
    If none exist, JSON is invalid, or schema validation fails, return None (deterministic soft-fail).
    """
    candidates = (
        overlay_dir / "manifest.json",
        overlay_dir / "overlay.json",
        overlay_dir / "yggdrasil.overlay.json",
    )
    for p in candidates:
        if not p.exists() or not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            # Validate contract; on failure treat as None (deterministic soft-fail)
            validate_overlay_manifest(d)
            return d
        except Exception:
            # JSON parse error or schema validation error - soft fail
            return None
    return None


def extract_declared_runes(manifest: Dict[str, Any]) -> Tuple[OverlayRuneDecl, ...]:
    """
    Supported overlay manifest shape (minimal):
    {
      "runes": [
        {"id": "abraxas.detectors.shadow.compliance_vs_remix", "depends_on": ["..."], "tags": ["shadow","detector"]}
      ]
    }
    """
    runes = manifest.get("runes", [])
    out: List[OverlayRuneDecl] = []
    if not isinstance(runes, list):
        return ()
    for r in runes:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id", "")).strip()
        if not rid:
            continue
        deps = r.get("depends_on", [])
        tags = r.get("tags", [])
        out.append(
            OverlayRuneDecl(
                rune_id=rid,
                depends_on=tuple(str(x) for x in deps) if isinstance(deps, list) else (),
                tags=tuple(str(x) for x in tags) if isinstance(tags, list) else (),
            )
        )
    # deterministic order
    out.sort(key=lambda x: x.rune_id)
    return tuple(out)
