"""
`aal_core` is split across two code roots in this repo:
- legacy/full implementation: `/workspace/aal_core`
- minimal/provenance-focused subset: `/workspace/src/aal_core`

Some tests intentionally prepend `/workspace/src` to `sys.path`. To keep imports
stable (and avoid duplicating modules), we extend this package's search path to
also include the legacy implementation directory when present.
"""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

# Allow pkgutil-style namespace spanning multiple directories.
__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

_workspace_root = Path(__file__).resolve().parents[2]
_legacy_pkg = _workspace_root / "aal_core"
if _legacy_pkg.exists():
    # Make `import aal_core.<anything>` also search the legacy package directory.
    p = str(_legacy_pkg)
    if p not in __path__:
        __path__.append(p)

