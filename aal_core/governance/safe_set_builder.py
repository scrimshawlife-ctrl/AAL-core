from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from abx_runes.tuning.hashing import content_hash

from aal_core.ers.effects_store import get_effect_stats, load_effects
from aal_core.ers.safe_set_store import SafeSetEntry, SafeSetStore, safe_set_key
from aal_core.ledger.ledger import EvidenceLedger


def _base_key(sig: Dict[str, str]) -> str:
    return ",".join(f"{k}={sig[k]}" for k in sorted(sig))


def _parse_base_key(bkey: str) -> Dict[str, str]:
    sig: Dict[str, str] = {}
    if not bkey:
        return sig
    for p in bkey.split(","):
        if "=" in p:
            k, v = p.split("=", 1)
            sig[k] = v
    return sig


def build_safe_sets(
    *,
    ledger: EvidenceLedger,
    store: SafeSetStore,
    tail_n: int = 20000,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Derive baseline-scoped safe sets from evidence:
    - tuning_attempted (attempt counts per value)
    - rollback_emitted (rollback attribution per (knob,value))
    - optional EffectStore guardrails per metric (baseline scoped)
    """
    policy = policy or {}
    min_attempts = int(policy.get("min_attempts", 10))
    safe_max_rr = float(policy.get("safe_max_rollback_rate", 0.05))
    decay_cycles = int(policy.get("safe_set_decay_cycles", 2000))

    # conservative optional effect sanity gate
    metric_name = str(policy.get("metric_name", "latency_ms_p95"))
    max_bad_metric_mean = float(policy.get("max_bad_metric_mean", 10.0))

    tail = ledger.read_tail(int(tail_n))
    now_idx = int(tail[-1]["idx"]) if tail else 0

    attempts = defaultdict(int)  # (mid, knob, val, base) -> n
    rollbacks = defaultdict(int)  # same key

    for ent in tail:
        t = ent.get("type")
        if t == "tuning_attempted":
            p = ent.get("payload") or {}
            mid = str(p.get("module_id", ""))
            knob = str(p.get("knob", ""))
            val = str(p.get("value", ""))
            sig = p.get("baseline_signature") or {}
            attempts[(mid, knob, val, _base_key(sig))] += 1
        elif t == "rollback_emitted":
            rb = (ent.get("payload") or {}).get("rollback") or {}
            mid = str(rb.get("module_id", ""))
            sig = rb.get("baseline_signature") or {}
            bkey = _base_key(sig)
            for knob, val in (rb.get("attempted_assignments") or {}).items():
                rollbacks[(mid, str(knob), str(val), bkey)] += 1

    effects = load_effects()
    effects_hash = content_hash(effects.to_dict())
    policy_hash = content_hash(policy)

    safe_values_by: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    support_by: Dict[Tuple[str, str, str], Dict[str, Any]] = defaultdict(dict)

    for (mid, knob, val, bkey), at in sorted(attempts.items()):
        if at < min_attempts:
            continue
        rb = rollbacks.get((mid, knob, val, bkey), 0)
        rr = float(rb) / float(at) if at > 0 else 0.0
        if rr > safe_max_rr:
            continue

        # Optional effects gate: block values whose mean delta is consistently "bad"
        baseline_sig = _parse_base_key(bkey)
        st = get_effect_stats(
            effects,
            module_id=mid,
            knob=knob,
            value=val,
            baseline_signature=baseline_sig,
            metric_name=metric_name,
        )
        if st is not None:
            m = st.mean
            if m is not None and float(m) > max_bad_metric_mean:
                continue

        safe_values_by[(mid, knob, bkey)].append(val)
        support_by[(mid, knob, bkey)][val] = {"attempts": at, "rollbacks": rb, "rollback_rate": rr}

    set_count = 0
    for (mid, knob, bkey), vals in sorted(safe_values_by.items()):
        sig = _parse_base_key(bkey)

        numeric_vals: List[float] = []
        all_numeric = True
        for v in vals:
            try:
                numeric_vals.append(float(v))
            except Exception:
                all_numeric = False
                break

        if all_numeric and numeric_vals:
            mn = min(numeric_vals)
            mx = max(numeric_vals)
            entry = SafeSetEntry(
                set_idx=now_idx,
                until_idx=now_idx + decay_cycles,
                kind="numeric",
                safe_values=None,
                safe_min=float(mn),
                safe_max=float(mx),
                support={"values": list(vals), "per_value": support_by[(mid, knob, bkey)]},
                provenance={
                    "ledger_tail_hash": ledger.tail_hash(),
                    "effects_hash": effects_hash,
                    "policy_hash": policy_hash,
                },
            )
        else:
            entry = SafeSetEntry(
                set_idx=now_idx,
                until_idx=now_idx + decay_cycles,
                kind="enum",
                safe_values=sorted(vals),
                safe_min=None,
                safe_max=None,
                support={"per_value": support_by[(mid, knob, bkey)]},
                provenance={
                    "ledger_tail_hash": ledger.tail_hash(),
                    "effects_hash": effects_hash,
                    "policy_hash": policy_hash,
                },
            )

        key = safe_set_key(module_id=mid, knob=knob, baseline_signature=sig)
        store.set(key, entry)
        set_count += 1
        ledger.append(
            entry_type="safe_set_derived",
            payload={"safe_set_key": key, "entry": store.entries[key]},
            provenance={"effects_hash": effects_hash},
        )

    pruned = store.prune_expired(now_idx)
    if pruned:
        ledger.append(entry_type="safe_set_pruned", payload={"count": pruned}, provenance={"now_idx": now_idx})

    return {"set": set_count, "pruned": pruned, "now_idx": now_idx}

