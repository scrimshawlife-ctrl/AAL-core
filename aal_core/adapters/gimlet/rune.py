"""
AAL-GIMLET Rune Interface
ABX-Runes integration for gimlet.v0.inspect
"""

import json
import hashlib
from typing import Dict, Any, Optional

from .contracts import InspectResult, InspectMode
from .scan import normalize_input, cleanup_temp
from .identity import classify_identity
from .plan import build_integration_plan, build_optimization_roadmap
from .score import compute_gimlet_score
from .coupling import generate_coupling_map


def _canonical_json_dumps(obj: Any) -> str:
    """Deterministic JSON serialization"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _compute_manifest_hash(result: InspectResult) -> str:
    """Compute deterministic hash of inspect result"""
    result_dict = result.to_dict()
    blob = _canonical_json_dumps(result_dict).encode()
    return hashlib.sha256(blob).hexdigest()


def inspect(
    source_path: str,
    mode: str = "inspect",
    run_seed: Optional[str] = None,
    exclude_patterns: Optional[list[str]] = None,
    generate_coupling: bool = True
) -> Dict[str, Any]:
    """
    Rune: gimlet.v0.inspect

    Inspect codebase and produce deterministic analysis.

    Args:
        source_path: Path to directory or zip file
        mode: Operating mode (inspect|integrate|optimize|report)
        run_seed: Optional deterministic seed for provenance
        exclude_patterns: Optional glob patterns to exclude
        generate_coupling: Generate coupling map (default: True)

    Returns:
        Dict with:
            - result: InspectResult as dict
            - coupling_map: CouplingMap as dict (if generate_coupling=True)
            - abx_runes: Rune provenance metadata
    """
    # Validate mode
    try:
        inspect_mode = InspectMode(mode)
    except ValueError:
        raise ValueError(f"Invalid mode: {mode}. Must be one of: inspect, integrate, optimize, report")

    # Phase 1: Normalize input
    file_map, provenance, temp_dir = normalize_input(
        source_path=source_path,
        mode=inspect_mode,
        run_seed=run_seed,
        exclude_patterns=exclude_patterns
    )

    try:
        # Phase 2: Classify identity
        identity = classify_identity(file_map, source_path)

        # Phase 3: Build integration or optimization plan
        integration_plan = build_integration_plan(file_map, identity)
        optimization_roadmap = None

        if identity.kind.value == "EXTERNAL":
            optimization_roadmap = build_optimization_roadmap(file_map)

        # Phase 4: Compute score
        score = compute_gimlet_score(file_map, identity, integration_plan, optimization_roadmap)

        # Phase 5: Build result
        result = InspectResult(
            provenance=provenance,
            file_map=file_map,
            identity=identity,
            integration_plan=integration_plan,
            optimization_roadmap=optimization_roadmap,
            score=score
        )

        # Phase 6: Generate coupling map (optional)
        coupling_map_dict = None
        if generate_coupling:
            coupling_map = generate_coupling_map(file_map, identity, source_path, run_seed)
            coupling_map_dict = coupling_map.to_dict()

        # Phase 7: Attach ABX-Runes metadata
        result_dict = result.to_dict()
        manifest_hash = _compute_manifest_hash(result)

        response = {
            "result": result_dict,
            "abx_runes": {
                "used": ["gimlet.v0.inspect"],
                "gate_state": "active",  # GIMLET is always active
                "manifest_sha256": manifest_hash,
                "vendor_lock_sha256": manifest_hash,  # For determinism proof
                "provenance": {
                    "artifact_hash": provenance.artifact_hash,
                    "run_seed": run_seed,
                    "tool_version": provenance.tool_version,
                    "mode": mode,
                }
            }
        }

        if coupling_map_dict:
            response["coupling_map"] = coupling_map_dict

        return response

    finally:
        # Clean up temp directory if created
        cleanup_temp(temp_dir)


# Rune registry entry
GIMLET_RUNE_DESCRIPTOR = {
    "id": "gimlet.v0.inspect",
    "name": "GIMLET Inspect",
    "kind": "adapter",
    "version": "0.1.0",
    "owner": "aal-core",
    "inputs_schema": {
        "type": "object",
        "required": ["source_path"],
        "properties": {
            "source_path": {"type": "string", "description": "Path to directory or zip file"},
            "mode": {
                "type": "string",
                "enum": ["inspect", "integrate", "optimize", "report"],
                "default": "inspect"
            },
            "run_seed": {"type": "string", "description": "Optional deterministic seed"},
            "exclude_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Glob patterns to exclude"
            }
        }
    },
    "outputs_schema": {
        "type": "object",
        "required": ["result", "abx_runes"],
        "properties": {
            "result": {"type": "object"},
            "abx_runes": {"type": "object"}
        }
    },
    "capabilities": ["inspect", "classify", "score", "plan"],
    "provenance": {
        "source": "aal_core.adapters.gimlet.rune",
        "canon": "AAL-GIMLET",
        "schema_version": "rune-descriptor/0.1"
    }
}


# Export for function registry
EXPORTS = [GIMLET_RUNE_DESCRIPTOR]
