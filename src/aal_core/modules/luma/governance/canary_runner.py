from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ..contracts.canary_ir import CanaryItem, CanaryReport
from ..contracts.proposal_ir import PatternProposal
from .ledger import ledger_status, load_ledger


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_semantic_dependencies(spec: Dict[str, Any]) -> List[str]:
    deps = set()
    for mapping in spec.get("mappings", []):
        src = mapping.get("source")
        if src:
            deps.add(src)
    for ch in (spec.get("channels") or {}).values():
        if isinstance(ch, str):
            deps.add(ch)
    return sorted(deps)


def _suggest_steps(spec: Dict[str, Any]) -> List[str]:
    steps = [
        "Define pattern class skeleton (no rendering logic)",
        "Add validate() enforcing spec semantic constraints",
        "Add compile() emitting renderer-agnostic plan",
        "Add golden determinism tests (12-run invariance)",
        "Implement minimal SVG renderer support (static only)",
        "Add documentation + risk notes",
        "Run canary comparison vs baseline patterns",
    ]

    primitives = spec.get("primitives", [])
    insert_at = 4
    if "chord" in primitives:
        steps.insert(
            0,
            "Adopt density heuristic: prefer chord when transfer_pair_count > 8; "
            "otherwise sankey",
        )
    if "chord" in primitives:
        steps.insert(insert_at, "Implement arc routing with deterministic ordering")
        insert_at += 1
    if "matrix" in primitives:
        steps.insert(insert_at, "Implement grid cell layout with fixed ordering")
        insert_at += 1
    if "heatmap" in primitives:
        steps.insert(insert_at, "Implement value→opacity mapping (bounded)")
        insert_at += 1
    if "timeline" in primitives:
        steps.insert(insert_at, "Implement time axis normalization (no animation)")

    return steps


class CanaryRunner:
    runner_id = "luma.canary.runner"
    runner_version = "0.1.0"

    def run(
        self, proposals: List[PatternProposal], ledger_path: str, scene_hash: str
    ) -> CanaryReport:
        ledger_obj = load_ledger(ledger_path)
        statuses = ledger_status(ledger_obj)

        accepted = [
            p for p in proposals if statuses.get(p.proposal_id) == "accepted_for_canary"
        ]

        items: List[CanaryItem] = []
        for p in sorted(accepted, key=lambda x: x.proposal_id):
            spec = p.pattern_spec
            deps = _extract_semantic_dependencies(spec)

            items.append(
                CanaryItem(
                    proposal_id=p.proposal_id,
                    pattern_id=spec.get("pattern_id"),
                    base_patterns=p.base_patterns,
                    semantic_dependencies=deps,
                    intended_gain=p.scores,
                    risks=p.risks,
                    suggested_steps=_suggest_steps(spec),
                )
            )

        return CanaryReport(
            schema="LumaCanaryReport.v0",
            scene_hash=scene_hash,
            generated_utc=_now_utc(),
            items=items,
            provenance={
                "runner": {"id": self.runner_id, "version": self.runner_version},
                "ledger_path": ledger_path,
            },
        )
