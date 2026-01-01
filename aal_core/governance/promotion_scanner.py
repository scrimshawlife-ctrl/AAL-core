from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from abx_runes.tuning.hashing import content_hash
from aal_core.ers.effects_store import EffectStore, load_effects, stderr, variance
from aal_core.ledger.ledger import EvidenceLedger


def _parse_effect_key(effect_key: str) -> Optional[Tuple[str, str, str, str, str]]:
    """
    EffectStore key format (v0.7 bucketed):
      module::knob::value::k=v,k=v::metric

    Returns: (module_id, knob, value, baseline_key, metric_name)
    """
    parts = effect_key.split("::")
    if len(parts) != 5:
        return None
    return parts[0], parts[1], parts[2], parts[3], parts[4]


def _baseline_dict(baseline_key: str) -> Dict[str, str]:
    if not baseline_key:
        return {}
    out: Dict[str, str] = {}
    for p in baseline_key.split(","):
        if "=" in p:
            k, v = p.split("=", 1)
            out[str(k)] = str(v)
    return out


def scan_for_promotions(
    *,
    source_cycle_id: str,
    ledger: EvidenceLedger,
    effects_path: str = ".aal/effects_store.json",
    tail_n: int = 2000,
    policy: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Deterministic promotion proposal generator:
    - reads EffectStore stats (mean/variance) from effects_path
    - estimates rollback rate conservatively from ledger tail
    - emits PromotionProposalIR-shaped dicts (shadow-only proposals)

    Rollback attribution is intentionally conservative in v1.4:
    rollback events are counted at (module_id, baseline_bucket) granularity.
    """
    policy = policy or {}
    min_samples = int(policy.get("min_samples", 12))
    z_threshold = float(policy.get("z_threshold", 3.0))
    min_abs = float(policy.get("min_abs_effect", 1.0))
    max_rollback_rate = float(policy.get("max_rollback_rate", 0.10))
    metrics = list(policy.get("metrics", ["latency_ms_p95", "cost_units", "error_rate", "throughput_per_s"]))

    store: EffectStore = load_effects(effects_path)

    tail = ledger.read_tail(int(tail_n))
    rollback_counts: Dict[Tuple[str, str], int] = defaultdict(int)  # (module_id, baseline_key) -> rollbacks
    trial_counts: Dict[str, int] = defaultdict(int)  # baseline_key -> "trial opportunity"

    def _baseline_key_from_sig(sig: Dict[str, str]) -> str:
        return ",".join(f"{k}={sig[k]}" for k in sorted(sig))

    for ent in tail:
        et = ent.get("type")
        payload = ent.get("payload") or {}

        if et == "rollback_emitted":
            rb = (payload.get("rollback") or {}) if isinstance(payload, dict) else {}
            mid = str(rb.get("module_id", ""))
            base = rb.get("baseline_signature") or {}
            base_key = _baseline_key_from_sig(base) if isinstance(base, dict) else ""
            rollback_counts[(mid, base_key)] += 1
            continue

        if et in ("bundle_emitted", "portfolio_applied", "experiment_executed"):
            base: Dict[str, str] = {}
            if et == "bundle_emitted":
                base = ((payload.get("bundle") or {}).get("baseline_signature") or {}) if isinstance(payload, dict) else {}
            elif et == "portfolio_applied":
                base = (payload.get("baseline_signature") or {}) if isinstance(payload, dict) else {}
            elif et == "experiment_executed":
                base = (payload.get("baseline_signature") or {}) if isinstance(payload, dict) else {}
            base_key = _baseline_key_from_sig(base) if isinstance(base, dict) else ""
            trial_counts[base_key] += 1

    proposals: List[Dict[str, Any]] = []
    ledger_tail_hash = ledger.tail_hash()
    effects_hash = content_hash(store.to_jsonable())
    policy_hash = content_hash(policy)

    # Evidence window per contract
    start_idx = int(tail[0]["idx"]) if tail else 0
    end_idx = int(tail[-1]["idx"]) if tail else 0
    entry_hashes_sampled = [str(e.get("entry_hash", "")) for e in tail[: min(25, len(tail))]]

    for effect_key in sorted(store.stats_by_key.keys()):
        parsed = _parse_effect_key(effect_key)
        if parsed is None:
            continue
        module_id, knob, value, baseline_key, metric_name = parsed
        if metric_name not in metrics:
            continue

        st = store.stats_by_key.get(effect_key)
        if st is None:
            continue
        if st.n < min_samples:
            continue

        mean = st.mean()
        if mean is None:
            continue
        if abs(float(mean)) < min_abs:
            continue

        se = stderr(st)
        if se is None or float(se) <= 0.0:
            continue
        z = abs(float(mean)) / float(se)
        if z < z_threshold:
            continue

        rb = rollback_counts.get((module_id, baseline_key), 0)
        tr = trial_counts.get(baseline_key, 0)
        rr = float(rb) / float(tr) if tr > 0 else 0.0
        if rr > max_rollback_rate:
            continue

        baseline_sig = _baseline_dict(baseline_key)
        proposal: Dict[str, Any] = {
            "schema_version": "promotion-proposal/0.1",
            "proposal_hash": "",
            "source_cycle_id": source_cycle_id,
            "target": {"module_id": module_id, "knob_name": knob, "value": value},
            "baseline_signature": baseline_sig,
            "metric_name": metric_name,
            "stats": {
                "n": int(st.n),
                "mean": float(mean),
                "variance": float(variance(st) or 0.0),
                "stderr": float(se),
                "z": float(z),
            },
            "rollback_rate": float(rr),
            "evidence_window": {
                "start_idx": int(start_idx),
                "end_idx": int(end_idx),
                "entry_hashes_sampled": entry_hashes_sampled,
            },
            "recommendation": {
                "action": "promote",
                "confidence": min(0.99, float(z) / (z_threshold * 2.0)),
            },
            "provenance": {
                "ledger_tail_hash": ledger_tail_hash,
                "effects_hash": effects_hash,
                "policy_hash": policy_hash,
            },
        }
        proposal["proposal_hash"] = content_hash({**proposal, "proposal_hash": ""})
        proposals.append(proposal)

    return proposals

