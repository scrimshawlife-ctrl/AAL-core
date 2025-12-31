"""
AAL-core Dynamic Function Registry (DFD)
=========================================
Deterministic function discovery across Abraxas + overlays.

Core Principles (SEED + ABX-Core):
- Deterministic: catalog is reproducible from same artifacts/manifests
- Provenance embedded: every entry includes repo/module/commit/hash
- Entropy minimization: bounded scanning only
- No hidden coupling: stable schema + bus events
- Capability sandbox: functions declare capabilities

DFD Rune (binding sigil): ᛞᚠᛞ ("DFD")
Meaning: Discovery → Catalog → Propagation
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .validate import validate_descriptors
from .sources.manifest import load_overlay_manifests
from .sources.py_entrypoints import load_py_exports
from .sources.http import fetch_remote_functions


# --------------------------------------------------
# Models
# --------------------------------------------------

@dataclass(frozen=True)
class CatalogSnapshot:
    """
    Immutable snapshot of the function catalog.

    Attributes:
        descriptors: List of FunctionDescriptor dicts
        catalog_hash: SHA256 hash of canonical JSON (state fingerprint)
        generated_at_unix: Unix timestamp when catalog was generated
    """
    descriptors: List[Dict[str, Any]]
    catalog_hash: str
    generated_at_unix: int

    @property
    def count(self) -> int:
        """Number of functions in catalog."""
        return len(self.descriptors)


# --------------------------------------------------
# Core Registry Service
# --------------------------------------------------

class FunctionRegistry:
    """
    Dynamic Function Discovery (DFD) Service.

    Builds a deterministic catalog from:
    1. Overlay manifests (.aal/overlays/<name>/manifest.json)
    2. Explicit Python exports (modules with EXPORTS list)
    3. Optional runtime HTTP handshake (GET /abx/functions)

    Emits bus event when catalog hash changes:
        Topic: fn.registry.updated
        Payload: {catalog_hash, generated_at_unix, count}

    Usage:
        registry = FunctionRegistry(bus, overlays_root="/path/to/.aal/overlays")
        registry.tick()  # Build catalog and emit update if changed
        snapshot = registry.get_snapshot()
    """

    def __init__(self, bus: Any, overlays_root: str):
        """
        Initialize the Function Registry.

        Args:
            bus: Event bus with publish(topic, payload) method
            overlays_root: Path to .aal/overlays directory
        """
        self._bus = bus
        self._overlays_root = overlays_root
        self._last_hash: Optional[str] = None
        self._snapshot: Optional[CatalogSnapshot] = None

    def _compute_catalog_hash(self, descriptors: List[Dict[str, Any]]) -> str:
        """
        Compute deterministic SHA256 hash of catalog.

        The hash is computed over canonical JSON:
        - Keys sorted alphabetically
        - Descriptors sorted by id
        - Compact separators (no whitespace)

        Args:
            descriptors: List of FunctionDescriptor dicts

        Returns:
            Hash string in format "sha256:<hex>"
        """
        canonical_json = json.dumps(
            descriptors,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

        digest = hashlib.sha256(canonical_json).hexdigest()
        return f"sha256:{digest}"

    def build_catalog(self) -> CatalogSnapshot:
        """
        Build function catalog from all discovery sources.

        Discovery order (stable):
        1. Load overlay manifests
        2. Load Python exports
        3. Fetch remote HTTP functions
        4. Merge by id (last wins)
        5. Sort by id
        6. Validate schema
        7. Compute hash

        Returns:
            Immutable CatalogSnapshot

        Raises:
            ValueError: If validation fails (missing fields, duplicate ids, etc.)
        """
        # 1. Load manifests
        manifests = load_overlay_manifests(self._overlays_root)

        # 2. Discover from all sources
        py_descriptors = load_py_exports(manifests)
        http_descriptors = fetch_remote_functions(manifests)

        # 3. Merge by id (deterministic: later sources override earlier)
        merged: Dict[str, Dict[str, Any]] = {}

        for descriptor in py_descriptors + http_descriptors:
            desc_id = descriptor.get("id")
            if desc_id:
                merged[desc_id] = descriptor

        # 4. Sort by id for determinism
        descriptors = [merged[key] for key in sorted(merged.keys())]

        # 5. Validate
        validate_descriptors(descriptors)

        # 6. Compute hash
        catalog_hash = self._compute_catalog_hash(descriptors)

        # 7. Create snapshot
        snapshot = CatalogSnapshot(
            descriptors=descriptors,
            catalog_hash=catalog_hash,
            generated_at_unix=int(time.time()),
        )

        self._snapshot = snapshot
        return snapshot

    def tick(self) -> None:
        """
        Rebuild catalog and emit bus event if hash changed.

        This should be called periodically (e.g., every 10s) or
        triggered by filesystem watch on overlay directories.

        Bus Event (on change):
            Topic: fn.registry.updated
            Payload: {
                "catalog_hash": str,
                "generated_at_unix": int,
                "count": int
            }
        """
        snapshot = self.build_catalog()

        # Emit event only if hash changed
        if snapshot.catalog_hash != self._last_hash:
            self._last_hash = snapshot.catalog_hash

            self._bus.publish(
                "fn.registry.updated",
                {
                    "catalog_hash": snapshot.catalog_hash,
                    "generated_at_unix": snapshot.generated_at_unix,
                    "count": snapshot.count,
                },
            )

    def get_snapshot(self) -> CatalogSnapshot:
        """
        Get current catalog snapshot.

        If no snapshot exists, builds one first.

        Returns:
            Current CatalogSnapshot
        """
        if self._snapshot is None:
            self.build_catalog()

        return self._snapshot  # type: ignore


# --------------------------------------------------
# FastAPI Integration
# --------------------------------------------------

def bind_fn_registry_routes(router: Any, fn_registry: FunctionRegistry) -> None:
    """
    Bind Function Registry routes to FastAPI router.

    Routes:
        GET /fn/catalog - Get full function catalog

    Args:
        router: FastAPI router or app
        fn_registry: FunctionRegistry instance
    """

    @router.get("/fn/catalog")
    def get_fn_catalog():
        """
        Get the current function catalog.

        Returns:
            {
                "catalog_hash": str,
                "generated_at_unix": int,
                "count": int,
                "functions": [<FunctionDescriptor>, ...]
            }
        """
        snapshot = fn_registry.get_snapshot()

        return {
            "catalog_hash": snapshot.catalog_hash,
            "generated_at_unix": snapshot.generated_at_unix,
            "count": snapshot.count,
            "functions": snapshot.descriptors,
        }
