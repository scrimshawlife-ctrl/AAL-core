from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


REALMS = {"ASGARD", "HEL", "MIDGARD", "NIFLHEIM", "MUSPELHEIM"}
LANES = {"shadow", "forecast", "neutral"}
PROMO = {"shadow", "candidate", "promoted", "deprecated", "archived"}


class OverlaySchemaError(Exception):
    """Raised when overlay manifest violates contract."""
    pass


def validate_overlay_manifest(d: Dict[str, Any]) -> None:
    """
    Minimal deterministic validator for overlay manifests.

    Validates against yggdrasil-overlay/0.1 contract:
    - schema_version must be "yggdrasil-overlay/0.1"
    - overlay.id is required (non-empty string)
    - runes array is optional but must follow schema if present
    - All enums (realm, lane, promotion_state) must be valid
    - Ports (inputs/outputs) must have name + dtype

    Fails fast with explicit reasons (deterministic error messages).
    """
    if not isinstance(d, dict):
        raise OverlaySchemaError("Manifest must be an object.")

    if d.get("schema_version") != "yggdrasil-overlay/0.1":
        raise OverlaySchemaError("schema_version must be 'yggdrasil-overlay/0.1'.")

    overlay = d.get("overlay")
    if not isinstance(overlay, dict):
        raise OverlaySchemaError("overlay must be an object.")

    oid = overlay.get("id")
    if not isinstance(oid, str) or not oid.strip():
        raise OverlaySchemaError("overlay.id must be a non-empty string.")

    if "default_realm" in overlay and overlay["default_realm"] not in REALMS:
        raise OverlaySchemaError("overlay.default_realm must be one of REALMS.")
    if "default_lane" in overlay and overlay["default_lane"] not in LANES:
        raise OverlaySchemaError("overlay.default_lane must be one of LANES.")

    runes = d.get("runes", [])
    if runes is None:
        return
    if not isinstance(runes, list):
        raise OverlaySchemaError("runes must be an array.")

    seen = set()
    for i, r in enumerate(runes):
        if not isinstance(r, dict):
            raise OverlaySchemaError(f"runes[{i}] must be an object.")
        rid = r.get("id")
        if not isinstance(rid, str) or not rid.strip():
            raise OverlaySchemaError(f"runes[{i}].id must be a non-empty string.")
        if rid in seen:
            raise OverlaySchemaError(f"Duplicate rune id: {rid}")
        seen.add(rid)

        if "depends_on" in r:
            if not isinstance(r["depends_on"], list) or not all(
                isinstance(x, str) and x.strip() for x in r["depends_on"]
            ):
                raise OverlaySchemaError(f"runes[{i}].depends_on must be an array of strings.")
        if "realm" in r and r["realm"] not in REALMS:
            raise OverlaySchemaError(f"runes[{i}].realm invalid.")
        if "lane" in r and r["lane"] not in LANES:
            raise OverlaySchemaError(f"runes[{i}].lane invalid.")
        if "promotion_state" in r and r["promotion_state"] not in PROMO:
            raise OverlaySchemaError(f"runes[{i}].promotion_state invalid.")

        for port_key in ("inputs", "outputs"):
            if port_key not in r:
                continue
            ports = r[port_key]
            if not isinstance(ports, list):
                raise OverlaySchemaError(f"runes[{i}].{port_key} must be an array.")
            for j, p in enumerate(ports):
                if not isinstance(p, dict):
                    raise OverlaySchemaError(f"runes[{i}].{port_key}[{j}] must be an object.")
                if not isinstance(p.get("name"), str) or not p["name"].strip():
                    raise OverlaySchemaError(f"runes[{i}].{port_key}[{j}].name required.")
                if not isinstance(p.get("dtype"), str) or not p["dtype"].strip():
                    raise OverlaySchemaError(f"runes[{i}].{port_key}[{j}].dtype required.")
                if "required" in p and not isinstance(p["required"], bool):
                    raise OverlaySchemaError(f"runes[{i}].{port_key}[{j}].required must be boolean.")
