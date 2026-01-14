from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Tuple

from aal_core.ers.cooldown import CooldownEntry, CooldownStore, cooldown_key
from aal_core.ledger.ledger import EvidenceLedger


def run_cooldown_scan(
    *,
    ledger: EvidenceLedger,
    store: CooldownStore,
    tail_n: int = 5000,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Ledger-driven cooldown scanner.

    Reads a tail window of the evidence ledger and computes rollback_rate per
    (module_id, knob, value, baseline_bucket). If rollback_rate exceeds policy
    threshold, sets a cooldown entry that expires after `cooldown_cycles` ledger indices.
    """
    policy = policy or {}
    max_rollback_rate = float(policy.get("max_rollback_rate", 0.25))
    cooldown_cycles = int(policy.get("cooldown_cycles", 250))

    tail = ledger.read_tail(int(tail_n))
    now_idx = int(tail[-1]["idx"]) if tail else 0

    attempts: dict[Tuple[str, str, str, str], int] = defaultdict(int)
    rollbacks: dict[Tuple[str, str, str, str], int] = defaultdict(int)

    def base_key(sig: Dict[str, str]) -> str:
        return ",".join(f"{k}={sig[k]}" for k in sorted(sig))

    for ent in tail:
        et = ent.get("entry_type")
        if et == "tuning_attempted":
            p = ent.get("payload") or {}
            mid = str(p.get("module_id", ""))
            knob = str(p.get("knob", ""))
            val = str(p.get("value", ""))
            sig = p.get("baseline_signature") or {}
            attempts[(mid, knob, val, base_key(sig))] += 1
        elif et == "rollback_emitted":
            rb = (ent.get("payload") or {}).get("rollback") or {}
            mid = str(rb.get("module_id", ""))
            sig = rb.get("baseline_signature") or {}
            bkey = base_key(sig)
            for knob, val in (rb.get("attempted_assignments") or {}).items():
                rollbacks[(mid, str(knob), str(val), bkey)] += 1

    set_count = 0
    for key, rb_count in sorted(rollbacks.items()):
        at_count = attempts.get(key, 0)
        if at_count <= 0:
            continue
        rr = float(rb_count) / float(at_count)
        if rr < max_rollback_rate:
            continue

        mid, knob, val, bkey = key
        sig: Dict[str, str] = {}
        if bkey:
            for p in bkey.split(","):
                if "=" in p:
                    k, v = p.split("=", 1)
                    sig[k] = v

        ck = cooldown_key(module_id=mid, knob=knob, value=val, baseline_signature=sig)
        if store.is_active(ck, now_idx):
            continue

        entry = CooldownEntry(
            set_idx=now_idx,
            until_idx=now_idx + cooldown_cycles,
            reason="rollback_rate_exceeded",
            stats_snapshot={"rollback_rate": rr, "rollbacks": rb_count, "attempts": at_count},
        )
        store.set(ck, entry)
        set_count += 1

        ledger.append(
            entry_type="cooldown_set",
            payload={"cooldown_key": ck, "entry": store.entries[ck]},
            provenance={"tail_n": int(tail_n)},
        )

    pruned = store.prune_expired(now_idx)
    if pruned:
        ledger.append(
            entry_type="cooldown_cleared",
            payload={"count": pruned},
            provenance={"now_idx": now_idx},
        )

    return {"set": set_count, "pruned": pruned, "now_idx": now_idx}

