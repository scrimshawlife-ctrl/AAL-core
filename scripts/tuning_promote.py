#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from abx_runes.tuning.emit import lock_tuning_ir
from abx_runes.tuning.hashing import canonical_json_dumps
from aal_core.ers.rent import RentThresholds, rent_paid


def load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote a TuningIR only if rent-payment thresholds are satisfied.")
    ap.add_argument("--tuning-ir", required=True)
    ap.add_argument("--metrics-before", required=True)
    ap.add_argument("--metrics-after", required=True)
    ap.add_argument("--evidence-bundle-hash", required=True, help="Verified evidence bundle hash authorizing this promotion")
    ap.add_argument("--max-latency-ms-p95", default="", help="Absolute threshold on AFTER p95 latency")
    ap.add_argument("--max-cost-units", default="")
    ap.add_argument("--max-error-rate", default="")
    ap.add_argument("--min-throughput-per-s", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ir = load_json(Path(args.tuning_ir))
    before = load_json(Path(args.metrics_before))
    after = load_json(Path(args.metrics_after))

    def _f(x: str):
        x = str(x).strip()
        return float(x) if x else None

    th = RentThresholds(
        max_latency_ms_p95=_f(args.max_latency_ms_p95),
        max_cost_units=_f(args.max_cost_units),
        max_error_rate=_f(args.max_error_rate),
        min_throughput_per_s=_f(args.min_throughput_per_s),
    )

    ok, reason = rent_paid(before, after, th)
    if not ok:
        print(f"FAIL: rent_not_paid:{reason}")
        return 5

    # Promote: change mode, embed evidence_bundle_hash, relock ir_hash deterministically
    out = dict(ir)
    out["mode"] = "promoted_tune"
    out["evidence_bundle_hash"] = str(args.evidence_bundle_hash).strip()
    out = lock_tuning_ir(out)

    Path(args.out).write_text(canonical_json_dumps(out) + "\n", encoding="utf-8")
    print(f"Wrote promoted TuningIR: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
