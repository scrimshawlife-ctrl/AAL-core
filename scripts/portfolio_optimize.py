#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from aal_core.ers.effects_store import load_effects
from abx_runes.tuning.emit import canonical_write
from abx_runes.tuning.portfolio.optimizer import build_portfolio
from abx_runes.tuning.portfolio.types import PortfolioPolicy


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True, help="registry snapshot json")
    ap.add_argument("--metrics", required=True, help="metrics snapshot json")
    ap.add_argument("--effects", default=str(Path(".aal/effects_store.json")), help="effects store path")
    ap.add_argument("--source-cycle-id", required=True)

    ap.add_argument("--min-samples", type=int, default=3)
    ap.add_argument("--min-abs-latency-ms-p95", type=float, default=1.0)
    ap.add_argument("--min-abs-cost-units", type=float, default=0.05)
    ap.add_argument("--min-abs-error-rate", type=float, default=0.001)
    ap.add_argument("--min-abs-throughput-per-s", type=float, default=0.2)
    ap.add_argument("--z-threshold", type=float, default=2.0)

    ap.add_argument("--max-changes-per-cycle", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    reg = _load_json(args.registry)
    met = _load_json(args.metrics)
    effects = load_effects(Path(args.effects))

    # Stabilization state is provided by the runtime; script uses an empty stub.
    class _DummyStab:
        cycles_since_change = {}

    policy = PortfolioPolicy(
        schema_version="portfolio-policy/0.1",
        source_cycle_id=str(args.source_cycle_id),
        max_changes_per_cycle=int(args.max_changes_per_cycle),
    )

    items, notes = build_portfolio(
        policy=policy,
        registry_snapshot=reg,
        metrics_snapshot=met,
        stabilization_state=_DummyStab(),
        effects_store=effects,
        min_samples=int(args.min_samples),
        min_abs_latency_ms_p95=float(args.min_abs_latency_ms_p95),
        min_abs_cost_units=float(args.min_abs_cost_units),
        min_abs_error_rate=float(args.min_abs_error_rate),
        min_abs_throughput_per_s=float(args.min_abs_throughput_per_s),
        z_threshold=float(args.z_threshold),
    )

    canonical_write(args.out, {"items": items, "notes": notes})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

