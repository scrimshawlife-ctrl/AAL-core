"""
Overlay registry for managing installed and enabled overlays.

Registry tracks overlay manifests and persists enabled state to disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .manifest import OverlayManifest


class OverlayRegistry:
    """
    Registry for managing overlay manifests and enabled state.

    Stores:
    - Individual manifests at .aal/overlays/<name>/manifest.json
    - Enabled overlays list at .aal/overlays/enabled.json
    """

    def __init__(self, base_path: str = ".aal/overlays"):
        """
        Initialize registry.

        Args:
            base_path: Base directory for overlay storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._enabled_path = self.base_path / "enabled.json"
        self._manifest_cache: Dict[str, OverlayManifest] = {}

    def _load_enabled_list(self) -> List[str]:
        """
        Load list of enabled overlay names from disk.

        Returns:
            List of enabled overlay names
        """
        if not self._enabled_path.exists():
            return []

        with open(self._enabled_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("enabled", [])

    def _save_enabled_list(self, enabled: List[str]) -> None:
        """
        Save list of enabled overlay names to disk.

        Args:
            enabled: List of overlay names to enable
        """
        with open(self._enabled_path, "w", encoding="utf-8") as f:
            json.dump({"enabled": sorted(enabled)}, f, indent=2)

    def install_manifest(self, manifest: OverlayManifest) -> None:
        """
        Install an overlay manifest.

        Args:
            manifest: OverlayManifest to install

        Raises:
            ValueError: If manifest is invalid
        """
        manifest.validate()
        manifest.save(str(self.base_path))
        self._manifest_cache[manifest.name] = manifest

    def uninstall(self, name: str) -> None:
        """
        Uninstall an overlay.

        Args:
            name: Name of overlay to uninstall

        Raises:
            ValueError: If overlay is currently enabled
        """
        if self.is_enabled(name):
            raise ValueError(f"Cannot uninstall enabled overlay '{name}'. Disable it first.")

        overlay_dir = self.base_path / name
        if overlay_dir.exists():
            import shutil
            shutil.rmtree(overlay_dir)

        if name in self._manifest_cache:
            del self._manifest_cache[name]

    def enable(self, name: str) -> None:
        """
        Enable an installed overlay.

        Args:
            name: Name of overlay to enable

        Raises:
            FileNotFoundError: If overlay is not installed
        """
        # Verify overlay exists
        manifest = self.get_manifest(name)  # Raises if not found

        enabled = self._load_enabled_list()
        if name not in enabled:
            enabled.append(name)
            self._save_enabled_list(enabled)

    def disable(self, name: str) -> None:
        """
        Disable an overlay.

        Args:
            name: Name of overlay to disable
        """
        enabled = self._load_enabled_list()
        if name in enabled:
            enabled.remove(name)
            self._save_enabled_list(enabled)

    def is_enabled(self, name: str) -> bool:
        """
        Check if an overlay is enabled.

        Args:
            name: Name of overlay

        Returns:
            True if enabled, False otherwise
        """
        return name in self._load_enabled_list()

    def list_installed(self) -> List[OverlayManifest]:
        """
        List all installed overlay manifests.

        Returns:
            List of OverlayManifest instances
        """
        manifests = []
        if not self.base_path.exists():
            return manifests

        for item in self.base_path.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                try:
                    manifest = OverlayManifest.load(item.name, str(self.base_path))
                    manifests.append(manifest)
                except Exception:
                    # Skip invalid manifests
                    continue

        return sorted(manifests, key=lambda m: m.name)

    def list_enabled(self) -> List[str]:
        """
        List names of enabled overlays.

        Returns:
            List of overlay names
        """
        return self._load_enabled_list()

    def get_manifest(self, name: str) -> OverlayManifest:
        """
        Get manifest for a specific overlay.

        Args:
            name: Overlay name

        Returns:
            OverlayManifest instance

        Raises:
            FileNotFoundError: If overlay is not installed
        """
        # Check cache first
        if name in self._manifest_cache:
            return self._manifest_cache[name]

        # Load from disk
        manifest = OverlayManifest.load(name, str(self.base_path))
        self._manifest_cache[name] = manifest
        return manifest

    def get_capability(self, capability: str) -> tuple[OverlayManifest, str]:
        """
        Resolve a capability to its overlay and capability name.

        Args:
            capability: Capability in format "overlay.capability" or just "capability"

        Returns:
            Tuple of (manifest, capability_name)

        Raises:
            ValueError: If capability cannot be resolved
        """
        # Parse capability string
        if "." in capability:
            overlay_name, cap_name = capability.split(".", 1)
        else:
            # Search enabled overlays for this capability
            for enabled_name in self.list_enabled():
                manifest = self.get_manifest(enabled_name)
                if capability in manifest.capabilities:
                    return manifest, capability
            raise ValueError(
                f"Capability '{capability}' not found in any enabled overlay"
            )

        # Get specific overlay
        manifest = self.get_manifest(overlay_name)

        if not self.is_enabled(manifest.name):
            raise ValueError(
                f"Overlay '{manifest.name}' is installed but not enabled"
            )

        if cap_name not in manifest.capabilities:
            raise ValueError(
                f"Capability '{cap_name}' not found in overlay '{manifest.name}'"
            )

        return manifest, cap_name

    def clear_cache(self) -> None:
        """Clear the internal manifest cache."""
        self._manifest_cache.clear()
