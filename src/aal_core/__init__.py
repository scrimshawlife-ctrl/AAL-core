"""
src/aal_core package root.

This repository contains additional `aal_core` modules in the repo-root `aal_core/`
directory. Some tests also prepend `src/` to `sys.path`, so we extend the package
search path to allow a single logical `aal_core.*` namespace across both locations.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

