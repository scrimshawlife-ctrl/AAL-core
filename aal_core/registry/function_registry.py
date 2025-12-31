"""Dynamic Function Registry (DFD) - Function discovery and catalog management."""
from __future__ import annotations
import hashlib
import json
import os
import time
import importlib
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CatalogSnapshot:
    """Immutable snapshot of the function catalog at a point in time."""
    descriptors: List[Dict[str, Any]]
    catalog_hash: str
    generated_at_unix: int


_REQUIRED_FIELDS = {
    "id", "name", "kind", "version", "owner",
    "inputs_schema", "outputs_schema",
    "capabilities", "provenance"
}


def validate_descriptors(desc: List[Dict[str, Any]]) -> None:
    """Validate function descriptors for required fields and uniqueness.

    Args:
        desc: List of function descriptor dictionaries

    Raises:
        ValueError: If required fields are missing or duplicate IDs found
    """
    seen = set()
    for d in desc:
        missing = _REQUIRED_FIELDS - d.keys()
        if missing:
            raise ValueError(f"Missing fields: {sorted(missing)}")
        if d["id"] in seen:
            raise ValueError(f"Duplicate id: {d['id']}")
        seen.add(d["id"])


def load_overlay_manifests(root: str) -> List[Dict[str, Any]]:
    """Load manifest.json files from overlay directories.

    Args:
        root: Path to overlays root directory (e.g., '.aal/overlays')

    Returns:
        List of manifest dictionaries with '_overlay' field added
    """
    items = []
    if not os.path.isdir(root):
        return items
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name, "manifest.json")
        if os.path.isfile(p):
            with open(p) as f:
                m = json.load(f)
            m["_overlay"] = name
            items.append(m)
    return items


def load_py_exports(manifests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Load Python-exported function descriptors from overlay manifests.

    Args:
        manifests: List of overlay manifest dictionaries

    Returns:
        Aggregated list of function descriptors from all py_exports

    Raises:
        TypeError: If EXPORTS is not a list in the module
    """
    out = []
    for m in manifests:
        for mod in m.get("py_exports", []):
            module = importlib.import_module(mod)
            exports = getattr(module, "EXPORTS", [])
            if not isinstance(exports, list):
                raise TypeError(f"{mod}.EXPORTS must be list[dict]")
            out.extend(exports)
    return out


def fetch_remote_functions(manifests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fetch function descriptors from remote service endpoints.

    Args:
        manifests: List of overlay manifest dictionaries

    Returns:
        Aggregated list of function descriptors from remote services

    Note:
        Failures are silently ignored (timeout, network errors, invalid JSON)
    """
    out = []
    for m in manifests:
        base = (m.get("service_url") or "").rstrip("/")
        if not base:
            continue
        try:
            with urllib.request.urlopen(f"{base}/abx/functions", timeout=1.5) as r:
                data = json.loads(r.read().decode())
                if isinstance(data.get("functions"), list):
                    out.extend(data["functions"])
        except Exception:
            continue
    return out


class FunctionRegistry:
    """Dynamic function registry with change detection and event publishing.

    Aggregates function descriptors from:
    - Python module exports (via manifest py_exports)
    - Remote service endpoints (via manifest service_url)

    Publishes 'fn.registry.updated' events to the bus when catalog changes.
    """

    def __init__(self, bus: Any, overlays_root: str):
        """Initialize the function registry.

        Args:
            bus: Event bus with publish(event: str, data: dict) method
            overlays_root: Path to overlays directory (e.g., '.aal/overlays')
        """
        self.bus = bus
        self.root = overlays_root
        self.last_hash: Optional[str] = None
        self.snapshot: Optional[CatalogSnapshot] = None

    def _hash(self, desc: List[Dict[str, Any]]) -> str:
        """Compute deterministic SHA256 hash of descriptor list.

        Args:
            desc: List of function descriptors

        Returns:
            Hash string in format 'sha256:<hex>'
        """
        blob = json.dumps(desc, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(blob).hexdigest()

    def build(self) -> CatalogSnapshot:
        """Build a fresh catalog snapshot from current sources.

        Returns:
            CatalogSnapshot with validated, deduplicated descriptors

        Raises:
            ValueError: If descriptors fail validation
        """
        m = load_overlay_manifests(self.root)
        desc = {}
        for d in load_py_exports(m) + fetch_remote_functions(m):
            desc[d["id"]] = d  # Deduplication by ID (last wins)
        ordered = [desc[k] for k in sorted(desc)]
        validate_descriptors(ordered)
        h = self._hash(ordered)
        snap = CatalogSnapshot(ordered, h, int(time.time()))
        self.snapshot = snap
        return snap

    def tick(self) -> None:
        """Rebuild catalog and publish update event if changed.

        Compares hash to detect changes. If changed, publishes
        'fn.registry.updated' event to bus with catalog metadata.
        """
        snap = self.build()
        if snap.catalog_hash != self.last_hash:
            self.last_hash = snap.catalog_hash
            self.bus.publish("fn.registry.updated", {
                "catalog_hash": snap.catalog_hash,
                "generated_at_unix": snap.generated_at_unix,
                "count": len(snap.descriptors),
            })

    def get_snapshot(self) -> CatalogSnapshot:
        """Get the current catalog snapshot (builds if not cached).

        Returns:
            CatalogSnapshot with current function catalog
        """
        return self.snapshot or self.build()
