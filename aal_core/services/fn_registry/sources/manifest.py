"""
AAL-core Function Registry: Manifest Source
Loads overlay manifests from .aal/overlays/
"""

import json
import os
from typing import Any, Dict, List


def load_overlay_manifests(overlays_root: str) -> List[Dict[str, Any]]:
    """
    Load all overlay manifests from overlays_root directory.

    Each manifest.json is enriched with "_overlay" field containing the overlay name.

    Args:
        overlays_root: Path to .aal/overlays directory

    Returns:
        List of manifest dictionaries, sorted by overlay name
    """
    manifests: List[Dict[str, Any]] = []

    if not os.path.isdir(overlays_root):
        return manifests

    for overlay_name in sorted(os.listdir(overlays_root)):
        overlay_path = os.path.join(overlays_root, overlay_name)

        # Skip non-directories
        if not os.path.isdir(overlay_path):
            continue

        manifest_path = os.path.join(overlay_path, "manifest.json")

        # Skip if no manifest
        if not os.path.isfile(manifest_path):
            continue

        # Load and enrich manifest
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            manifest["_overlay"] = overlay_name
            manifests.append(manifest)

        except (json.JSONDecodeError, OSError) as e:
            # Log but don't fail - partial discovery is acceptable
            print(f"Warning: Failed to load manifest for {overlay_name}: {e}")
            continue

    return manifests
