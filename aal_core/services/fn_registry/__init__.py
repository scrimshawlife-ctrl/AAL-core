# -*- coding: utf-8 -*-
"""
AAL-core Dynamic Function Registry (DFD)
DFD - Discovery, Catalog, Propagation
"""

from .service import (
    CatalogSnapshot,
    FunctionRegistry,
    bind_fn_registry_routes,
)
from .validate import (
    validate_descriptor,
    validate_descriptors,
    REQUIRED_FIELDS,
    VALID_KINDS,
)

__all__ = [
    "CatalogSnapshot",
    "FunctionRegistry",
    "bind_fn_registry_routes",
    "validate_descriptor",
    "validate_descriptors",
    "REQUIRED_FIELDS",
    "VALID_KINDS",
]
