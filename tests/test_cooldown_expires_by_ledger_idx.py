from pathlib import Path

from aal_core.ers.cooldown import CooldownStore
from aal_core.governance.cooldown_scanner import run_cooldown_scan
from aal_core.ledger.ledger import EvidenceLedger


def test_cooldown_expires_based_on_ledger_idx(tmp_path: Path) -> None:
    ledger = EvidenceLedger(path=tmp_path / "ledger.jsonl")
    store = CooldownStore(entries={})

    baseline_signature = {"bucket": "A"}

    # 4 attempts, 2 rollbacks => rollback_rate=0.5
    for _ in range(4):
        ledger.append(
            entry_type="tuning_attempted",
            payload={
                "module_id": "m",
                "knob": "k",
                "value": "1",
                "baseline_signature": baseline_signature,
            },
        )
    for _ in range(2):
        ledger.append(
            entry_type="rollback_emitted",
            payload={
                "rollback": {
                    "module_id": "m",
                    "baseline_signature": baseline_signature,
                    "attempted_assignments": {"k": "1"},
                }
            },
        )

    res1 = run_cooldown_scan(
        ledger=ledger,
        store=store,
        tail_n=50,
        policy={"max_rollback_rate": 0.25, "cooldown_cycles": 5},
    )
    assert res1["set"] == 1
    assert len(store.entries) == 1

    ck, entry = next(iter(store.entries.items()))
    until_idx = int(entry["until_idx"])

    # Advance ledger idx to (>= until_idx)
    last_idx = int(ledger.read_tail(1)[-1]["idx"])
    for _ in range(max(0, until_idx - last_idx)):
        ledger.append(entry_type="noop", payload={})

    res2 = run_cooldown_scan(
        ledger=ledger,
        store=store,
        tail_n=5,  # avoid re-setting based on old rollback window
        policy={"max_rollback_rate": 0.25, "cooldown_cycles": 5},
    )
    assert res2["pruned"] == 1
    assert ck not in store.entries

