from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from aal_core.ers.effects_store import load_effects
from abx_runes.tuning.hashing import canonical_json_dumps
from abx_runes.tuning.portfolio.emit import make_portfolio_ir
from abx_runes.tuning.portfolio.optimizer import build_portfolio
from abx_runes.tuning.portfolio.types import PortfolioPolicy


def load_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _opt_float(s: str) -> float | None:
    ss = str(s or "").strip()
    if not ss:
        return None
    return float(ss)


def main() -> int:
    ap = argparse.ArgumentParser(description="Portfolio optimize using measured deltas + noise guardrails (v0.5).")
    ap.add_argument("--registry-snapshot", required=True)
    ap.add_argument("--metrics-snapshot", required=True)
    ap.add_argument("--effects-store", default=".aal/effects_store.json")

    ap.add_argument("--source-cycle-id", required=True)
    ap.add_argument("--max-changes-per-cycle", type=int, default=4)
    ap.add_argument("--budget-cost-units", default="")
    ap.add_argument("--budget-latency-ms-p95", default="")

    # significance gates
    ap.add_argument("--min-samples", type=int, default=3)
    ap.add_argument("--min-abs-latency-ms-p95", type=float, default=1.0)
    ap.add_argument("--min-abs-cost-units", type=float, default=0.05)
    ap.add_argument("--min-abs-error-rate", type=float, default=0.001)
    ap.add_argument("--min-abs-throughput-per-s", type=float, default=0.2)
    ap.add_argument("--allow-unknown-effects-shadow-only", action="store_true")

    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    reg = load_json(args.registry_snapshot)
    met = load_json(args.metrics_snapshot)

    policy = PortfolioPolicy(
        schema_version="portfolio-policy/0.1",
        source_cycle_id=str(args.source_cycle_id),
        max_changes_per_cycle=int(args.max_changes_per_cycle),
        budget_cost_units=_opt_float(args.budget_cost_units),
        budget_latency_ms_p95=_opt_float(args.budget_latency_ms_p95),
    )

    # stabilization state is not loaded here (CLI tool); pass a dummy that always allows.
    class _Dummy:
        cycles_since_change: Dict[tuple[str, str], int] = {}

    stab = _Dummy()
    effects = load_effects(Path(args.effects_store))

    items, notes = build_portfolio(
        policy=policy,
        registry_snapshot=reg,
        metrics_snapshot=met,
        stabilization_state=stab,
        effects_store=effects,
        min_samples=int(args.min_samples),
        min_abs_latency_ms_p95=float(args.min_abs_latency_ms_p95),
        min_abs_cost_units=float(args.min_abs_cost_units),
        min_abs_error_rate=float(args.min_abs_error_rate),
        min_abs_throughput_per_s=float(args.min_abs_throughput_per_s),
        allow_unknown_effects_shadow_only=bool(args.allow_unknown_effects_shadow_only),
    )

    out = make_portfolio_ir(source_cycle_id=str(args.source_cycle_id), items=items, notes=notes)
    Path(args.out).write_text(canonical_json_dumps(out) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

