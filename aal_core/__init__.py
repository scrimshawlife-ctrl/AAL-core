"""AAL Core - Architecture Abstraction Layer for AAL-Core integrations and utilities.

This repo currently hosts a split package layout (`aal_core/` and `src/aal_core/`).
To keep imports stable under different `sys.path` orderings (some tests prepend `src`),
we explicitly extend the package search path so submodules can live in either location.
"""

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

# Prefer `src/aal_core` implementations (so `aal_core.bus` resolves to the package
# with `frame.py`, rather than the legacy `aal_core/bus.py` module).
_SRC_IMPL = (Path(__file__).resolve().parents[1] / "src" / "aal_core")
if _SRC_IMPL.exists():
    src_str = str(_SRC_IMPL)
    if src_str in __path__:
        __path__.remove(src_str)
    __path__.insert(0, src_str)
