"""
AAL-GIMLET Coupling Module
YAML-driven coupling map generation and rule evaluation.
"""

import yaml
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from fnmatch import fnmatch

from .contracts import FileMap, Identity, IdentityKind


@dataclass(frozen=True)
class CouplingRule:
    """Single coupling rule from default_rules.v0.yaml"""
    rule_id: str
    priority: int
    kind: IdentityKind
    capabilities: List[Dict[str, Any]]
    evidence_rules: List[str]


@dataclass(frozen=True)
class CouplingMap:
    """Generated coupling map for a codebase"""
    schema: str
    provenance: Dict[str, Any]
    policies: Dict[str, str]
    systems: List[Dict[str, Any]]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML serialization"""
        return {
            "schema": self.schema,
            "provenance": self.provenance,
            "policies": self.policies,
            "systems": self.systems,
            "notes": self.notes
        }

    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.to_dict(), sort_keys=False, default_flow_style=False)


def _load_default_rules() -> List[Dict[str, Any]]:
    """Load default rules from YAML file"""
    rules_path = Path(__file__).parent / "default_rules.v0.yaml"

    if not rules_path.exists():
        # Return minimal fallback rules
        return [
            {
                "id": "R900_default_external",
                "priority": 0,
                "when": {"always": True},
                "then": {
                    "kind": "EXTERNAL",
                    "couple": [
                        {"cap": "ingress.inspect", "rune": "gimlet.v0.inspect"}
                    ],
                    "evidence_rules": ["default_fallback"]
                }
            }
        ]

    with open(rules_path, "r") as f:
        rules_doc = yaml.safe_load(f)

    return rules_doc.get("rules", [])


def _evaluate_path_exists(file_map: FileMap, patterns: List[str]) -> bool:
    """Check if any file matches the glob patterns"""
    for pattern in patterns:
        for file_info in file_map.files:
            if fnmatch(file_info.path, pattern):
                return True
    return False


def _evaluate_text_match(file_map: FileMap, globs: List[str], patterns: List[str]) -> bool:
    """Check if any file matching globs contains the text patterns"""
    # Simplified: check if file paths contain pattern strings
    # Full implementation would parse file contents
    matching_files = []
    for glob_pattern in globs:
        for file_info in file_map.files:
            if fnmatch(file_info.path, glob_pattern):
                matching_files.append(file_info.path)

    # Heuristic: check if patterns appear in file paths
    for pattern in patterns:
        for file_path in matching_files:
            if pattern.lower() in file_path.lower():
                return True

    return False


def _evaluate_rule_condition(rule: Dict[str, Any], file_map: FileMap) -> bool:
    """Evaluate if a rule's condition matches the file map"""
    when = rule.get("when", {})

    # Always true
    if when.get("always"):
        return True

    # Path exists check
    if "any_path_exists" in when:
        patterns = when["any_path_exists"]
        if _evaluate_path_exists(file_map, patterns):
            return True

    # Text match check
    if "any_text_match" in when:
        globs = when["any_text_match"].get("globs", [])
        patterns = when["any_text_match"].get("patterns", [])
        if _evaluate_text_match(file_map, globs, patterns):
            return True

    return False


def generate_coupling_map(
    file_map: FileMap,
    identity: Identity,
    source_path: str,
    run_seed: Optional[str] = None
) -> CouplingMap:
    """
    Generate coupling map from file map and identity.

    Uses default_rules.v0.yaml to determine capabilities and rune couplings.

    Args:
        file_map: Normalized file map
        identity: Classified identity
        source_path: Original source path
        run_seed: Optional deterministic seed

    Returns:
        CouplingMap with deterministic coupling recommendations
    """
    import time

    # Load rules
    rules = _load_default_rules()

    # Sort by priority (highest first)
    rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

    # Find first matching rule
    matched_rule = None
    for rule in rules:
        if _evaluate_rule_condition(rule, file_map):
            matched_rule = rule
            break

    # Extract coupling from matched rule
    capabilities = []
    evidence_rules = []

    if matched_rule:
        then_clause = matched_rule.get("then", {})
        couple_list = then_clause.get("couple", [])
        evidence_rules = then_clause.get("evidence_rules", [])

        for coupling in couple_list:
            capabilities.append({
                "cap": coupling.get("cap"),
                "rune": coupling.get("rune"),
                "direction": coupling.get("direction", "consume"),
                "qos": coupling.get("qos", {
                    "latency_ms_budget": 500,
                    "ers_priority": 3
                }),
                "io_contract": coupling.get("io_contract", {}),
                "evidence": [
                    {"rule": rule} for rule in evidence_rules
                ]
            })

    # Detect entrypoints
    entrypoints = [
        f"{f.path}:main" for f in file_map.files if f.is_entrypoint
    ]

    if not entrypoints:
        entrypoints = ["<unknown>:main"]

    # Build system descriptor
    system = {
        "system_id": Path(source_path).name,
        "kind": identity.kind.value,
        "entrypoints": entrypoints,
        "capabilities": capabilities
    }

    # Compute artifact hash
    artifact_data = {
        "file_count": file_map.file_count,
        "total_size": file_map.total_size_bytes,
        "languages": file_map.languages,
        "identity": identity.kind.value
    }
    artifact_hash = hashlib.sha256(
        json.dumps(artifact_data, sort_keys=True).encode()
    ).hexdigest()

    # Build provenance
    provenance = {
        "artifact_hash": artifact_hash,
        "generated_by": "aal-gimlet",
        "seed": run_seed or "0",
        "run_id": f"gimlet-{int(time.time())}"
    }

    # Build coupling map
    coupling_map = CouplingMap(
        schema="coupling_map.v0",
        provenance=provenance,
        policies={
            "coupling": "abx-runes-only",
            "determinism": "seeded",
            "sandbox": "capability",
            "scheduler": "ers"
        },
        systems=[system],
        notes=[
            "Generated by AAL-GIMLET",
            f"Identity: {identity.kind.value}",
            f"Confidence: {identity.confidence:.2f}",
            f"Matched rule: {matched_rule.get('id', 'unknown') if matched_rule else 'none'}"
        ]
    )

    return coupling_map


def load_rune_catalog() -> Dict[str, Any]:
    """Load canonical rune catalog from YAML"""
    catalog_path = Path(__file__).parent.parent.parent / "runes" / "catalog.v0.yaml"

    if not catalog_path.exists():
        # Return minimal catalog
        return {
            "schema": "rune_catalog.v0",
            "runes": [
                {
                    "rune_id": "gimlet.v0.inspect",
                    "provides": ["ingress.inspect", "ingress.classify"],
                    "io": {"in": "GimletIn.v0", "out": "GimletReport.v0"}
                }
            ]
        }

    with open(catalog_path, "r") as f:
        return yaml.safe_load(f)


def get_rune_capabilities(rune_id: str) -> List[str]:
    """Get capabilities provided by a rune"""
    catalog = load_rune_catalog()

    for rune in catalog.get("runes", []):
        if rune.get("rune_id") == rune_id:
            return rune.get("provides", [])

    return []
