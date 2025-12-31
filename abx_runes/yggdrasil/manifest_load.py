from __future__ import annotations

from pathlib import Path

from .io import load_manifest_dict
from .schema import (
    GovernanceSpec,
    Lane,
    NodeKind,
    PortSpec,
    PromotionState,
    ProvenanceSpec,
    Realm,
    RuneLink,
    StabilizationSpec,
    YggdrasilManifest,
    YggdrasilNode,
)


def load_structured_manifest(path: Path) -> YggdrasilManifest:
    """
    Deterministically parse a yggdrasil.manifest.json into typed dataclasses.
    """
    d = load_manifest_dict(path)
    prov = d["provenance"]
    provenance = ProvenanceSpec(
        schema_version=str(prov["schema_version"]),
        manifest_hash=str(prov.get("manifest_hash", "")),
        created_at=str(prov.get("created_at", "")),
        updated_at=str(prov.get("updated_at", "")),
        source_commit=str(prov.get("source_commit", "")),
    )

    nodes = []
    for n in d.get("nodes", []):
        nodes.append(
            YggdrasilNode(
                id=str(n["id"]),
                kind=NodeKind(str(n["kind"])),
                realm=Realm(str(n["realm"])),
                lane=Lane(str(n["lane"])),
                authority_level=int(n["authority_level"]),
                parent=n.get("parent"),
                depends_on=tuple(n.get("depends_on", [])),
                inputs=tuple(PortSpec(**p) for p in n.get("inputs", []) or []),
                outputs=tuple(PortSpec(**p) for p in n.get("outputs", []) or []),
                promotion_state=PromotionState(str(n.get("promotion_state", "shadow"))),
                stabilization=StabilizationSpec(**(n.get("stabilization", {}) or {})),
                governance=GovernanceSpec(
                    rent_metrics=tuple((n.get("governance", {}) or {}).get("rent_metrics", []) or []),
                    gates_required=tuple((n.get("governance", {}) or {}).get("gates_required", []) or []),
                ),
            )
        )

    links = []
    for l in d.get("links", []) or []:
        links.append(
            RuneLink(
                id=str(l["id"]),
                from_node=str(l["from_node"]),
                to_node=str(l["to_node"]),
                allowed_lanes=tuple(l.get("allowed_lanes", []) or []),
                data_class=str(l.get("data_class", "feature")),
                determinism_rule=str(l.get("determinism_rule", "stable_sort_by_id")),
                failure_mode=str(l.get("failure_mode", "not_computable")),
                evidence_required=tuple(l.get("evidence_required", []) or []),
                required_evidence_ports=tuple(PortSpec(**p) for p in (l.get("required_evidence_ports", []) or [])),
            )
        )

    return YggdrasilManifest(provenance=provenance, nodes=tuple(nodes), links=tuple(links))
