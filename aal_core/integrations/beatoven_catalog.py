# ==========================================
# AAL-core : BeatOven Metrics Integration Layer (Optional)
# ==========================================
# Purpose:
# - Consume the FunctionRegistry catalog
# - Provide helper utilities to:
#     (a) filter metrics/ops by owner
#     (b) aggregate capabilities
#     (c) (optionally) run a metric by entrypoint (python only)
#
# This does NOT replace the registry.
# It is a thin, deterministic helper module.
#
# Suggested path:
#   aal_core/integrations/beatoven_catalog.py
# ==========================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable
import importlib


# -------------------------------
# Catalog helpers
# -------------------------------

def filter_by_owner(functions: List[Dict[str, Any]], owner: str) -> List[Dict[str, Any]]:
    return [f for f in functions if f.get("owner") == owner]

def filter_by_kind(functions: List[Dict[str, Any]], kind: str) -> List[Dict[str, Any]]:
    return [f for f in functions if f.get("kind") == kind]

def capabilities_union(functions: List[Dict[str, Any]]) -> List[str]:
    caps = set()
    for f in functions:
        for c in f.get("capabilities", []) or []:
            caps.add(c)
    return sorted(caps)

def summarize_owner(functions: List[Dict[str, Any]], owner: str) -> Dict[str, Any]:
    owned = filter_by_owner(functions, owner)
    return {
        "owner": owner,
        "count": len(owned),
        "kinds": sorted({f.get("kind") for f in owned}),
        "capabilities": capabilities_union(owned),
        "ids": sorted([f.get("id") for f in owned]),
    }


# -------------------------------
# Optional local execution utility (Python entrypoints only)
# -------------------------------
# NOTE:
# - Deterministic behavior depends on stable imports and stable function code.
# - This utility should only be used when the overlay is installed in the same env.
# - HTTP execution is a separate layer (router/executor), not included here.

def _load_entrypoint(entrypoint: str) -> Callable:
    """
    entrypoint format: "module.path:function_name"
    """
    if ":" not in entrypoint:
        raise ValueError(f"Invalid entrypoint format (expected module:function): {entrypoint}")
    mod_name, fn_name = entrypoint.split(":", 1)
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, fn_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"Entrypoint not callable: {entrypoint}")
    return fn

def run_metric_from_catalog(
    catalog_functions: List[Dict[str, Any]],
    metric_id: str,
    payload: Dict[str, Any],
    require_owner: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a metric by id using its python entrypoint.
    Guards:
      - optional require_owner (e.g., "beatoven")
      - kind must be "metric"
    """
    match = None
    for f in catalog_functions:
        if f.get("id") == metric_id:
            match = f
            break

    if match is None:
        raise KeyError(f"Metric id not found in catalog: {metric_id}")

    if match.get("kind") != "metric":
        raise ValueError(f"Requested id is not a metric: {metric_id}")

    if require_owner and match.get("owner") != require_owner:
        raise ValueError(f"Owner mismatch for {metric_id}: expected {require_owner}, got {match.get('owner')}")

    entrypoint = match.get("entrypoint")
    if not isinstance(entrypoint, str):
        raise ValueError(f"Missing/invalid entrypoint for {metric_id}")

    fn = _load_entrypoint(entrypoint)
    return fn(payload)


# -------------------------------
# BeatOven-specific convenience
# -------------------------------

BEATOVEN_OWNER = "beatoven"

def beatoven_metrics(functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return filter_by_kind(filter_by_owner(functions, BEATOVEN_OWNER), "metric")

def beatoven_ops(functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return filter_by_kind(filter_by_owner(functions, BEATOVEN_OWNER), "overlay_op")

def beatoven_summary(functions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return summarize_owner(functions, BEATOVEN_OWNER)

"""
USAGE EXAMPLE (inside an AAL-core service):
-----------------------------------------
snap = fn_registry.get_snapshot()
print(beatoven_summary(snap.descriptors))

# Run a BeatOven metric locally (if beatoven is installed in same env)
out = run_metric_from_catalog(
    snap.descriptors,
    metric_id="beatoven.metric.gsi.v1",
    payload={"onsets_ms":[0,125,250,380], "grid_ms":125},
    require_owner="beatoven"
)
print(out)
"""
