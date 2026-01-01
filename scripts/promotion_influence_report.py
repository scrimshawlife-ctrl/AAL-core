#!/usr/bin/env python3
"""
Emit promotion influence report to evidence ledger.

Usage:
    python scripts/promotion_influence_report.py --bundle-file <bundle.json>

Reads tuning plane bundle with promotion_report annotation and emits
one ledger event per cycle.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aal_core.ledger.ledger import EvidenceLedger


def emit_promotion_influence(
    bundle: dict,
    ledger: EvidenceLedger,
) -> None:
    """
    Emit promotion influence report from bundle to ledger.

    One compact artifact per cycle. No per-candidate spam.
    """
    promotion_report = bundle.get("promotion_report") or {}
    if not promotion_report:
        print("No promotion_report in bundle. Skipping.", file=sys.stderr)
        return

    # Aggregate across all modules
    total_candidates = 0
    total_promotion_biased = 0
    total_selected_with_promotion = 0
    modules_with_promotions = []
    total_dormant = 0

    for module_id, report in promotion_report.items():
        total_candidates += int(report.get("candidates_total", 0))
        total_promotion_biased += int(report.get("promotion_biased", 0))
        total_selected_with_promotion += int(report.get("selected_with_promotion", 0))
        total_dormant += int(report.get("dormant_promotions", 0))
        if int(report.get("selected_with_promotion", 0)) > 0:
            modules_with_promotions.append(module_id)

    # Emit single ledger event
    payload = {
        "schema_version": "promotion-influence-report/0.1",
        "source_cycle_id": str(bundle.get("source_cycle_id", "")),
        "bundle_hash": str(bundle.get("bundle_hash", "")),
        "candidates_total": total_candidates,
        "promotion_biased": total_promotion_biased,
        "selected_with_promotion": total_selected_with_promotion,
        "modules_with_promotions": modules_with_promotions,
        "dormant_promotions": total_dormant,
        "per_module": dict(promotion_report),
    }

    result = ledger.append(
        entry_type="promotion_influence_reported",
        payload=payload,
        provenance={
            "bundle_schema": str(bundle.get("schema_version", "")),
            "baseline_signature": bundle.get("baseline_signature") or {},
        },
    )

    print(f"✅ Promotion influence reported (idx={result.idx})", file=sys.stderr)
    print(json.dumps(result.entry, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit promotion influence report to ledger")
    parser.add_argument("--bundle-file", required=True, help="Path to tuning plane bundle JSON")
    parser.add_argument("--ledger-path", help="Path to evidence ledger (default: .aal/evidence_ledger.jsonl)")

    args = parser.parse_args()

    bundle_path = Path(args.bundle_file)
    if not bundle_path.exists():
        print(f"❌ Bundle file not found: {bundle_path}", file=sys.stderr)
        sys.exit(1)

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    ledger_path = Path(args.ledger_path) if args.ledger_path else None
    ledger = EvidenceLedger(path=ledger_path) if ledger_path else EvidenceLedger()

    emit_promotion_influence(bundle, ledger)


if __name__ == "__main__":
    main()
