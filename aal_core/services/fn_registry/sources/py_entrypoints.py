"""
AAL-core Function Registry: Python Exports Source
Discovers functions from explicit Python module exports.
"""

import importlib
from typing import Any, Dict, List


def load_py_exports(manifests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Load function descriptors from Python modules.

    Manifests may include:
      "py_exports": ["abraxas.exports", "psyfi_overlay.exports"]

    Each module MUST define:
      EXPORTS: list[dict]

    where each dict is a valid FunctionDescriptor.

    Args:
        manifests: List of overlay manifests

    Returns:
        List of FunctionDescriptor dicts from all py_exports modules

    Raises:
        TypeError: If EXPORTS is not a list
        ImportError: If py_exports module cannot be imported
    """
    descriptors: List[Dict[str, Any]] = []

    for manifest in manifests:
        py_exports = manifest.get("py_exports") or []

        if not isinstance(py_exports, list):
            overlay_name = manifest.get("_overlay", "unknown")
            print(f"Warning: {overlay_name} py_exports must be a list, got {type(py_exports)}")
            continue

        for module_name in py_exports:
            try:
                # Import the module
                module = importlib.import_module(module_name)

                # Get EXPORTS attribute
                exports = getattr(module, "EXPORTS", None)

                if exports is None:
                    print(f"Warning: {module_name} has no EXPORTS attribute")
                    continue

                if not isinstance(exports, list):
                    raise TypeError(
                        f"{module_name}.EXPORTS must be list[dict], got {type(exports)}"
                    )

                # Extend descriptors
                descriptors.extend(exports)

            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")
                continue

            except Exception as e:
                print(f"Warning: Error loading exports from {module_name}: {e}")
                continue

    return descriptors
