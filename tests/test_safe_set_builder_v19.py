from __future__ import annotations

from pathlib import Path

from aal_core.ers.effects_store import EffectStore
from aal_core.ers.safe_set_store import SafeSetEntry, SafeSetStore, safe_set_key
from aal_core.governance.safe_set_builder import build_safe_sets
from aal_core.ledger.ledger import EvidenceLedger


def _attempt(ledger: EvidenceLedger, *, mid: str, knob: str, value: str, baseline: dict[str, str]) -> None:
    ledger.append(
        entry_type="tuning_attempted",
        payload={"module_id": mid, "knob": knob, "value": value, "baseline_signature": baseline},
        provenance={},
    )


def _rollback(ledger: EvidenceLedger, *, mid: str, baseline: dict[str, str], assigns: dict[str, str]) -> None:
    ledger.append(
        entry_type="rollback_emitted",
        payload={"rollback": {"module_id": mid, "baseline_signature": baseline, "attempted_assignments": assigns}},
        provenance={},
    )


def test_derived_safe_values_only_include_low_rr(monkeypatch, tmp_path: Path):
    # Avoid filesystem dependency on effects persistence.
    monkeypatch.setattr("aal_core.governance.safe_set_builder.load_effects", lambda: EffectStore())

    ledger = EvidenceLedger(path=tmp_path / "ledger.jsonl")
    store = SafeSetStore(entries={})

    baseline = {"mode": "m0"}
    for _ in range(10):
        _attempt(ledger, mid="mod", knob="k", value="A", baseline=baseline)
        _attempt(ledger, mid="mod", knob="k", value="B", baseline=baseline)

    # One rollback for B => rr = 1/10 = 0.1 (blocked under 0.05)
    _rollback(ledger, mid="mod", baseline=baseline, assigns={"k": "B"})

    res = build_safe_sets(
        ledger=ledger,
        store=store,
        tail_n=1000,
        policy={"min_attempts": 10, "safe_max_rollback_rate": 0.05, "safe_set_decay_cycles": 100},
    )
    assert res["set"] == 1

    key = safe_set_key(module_id="mod", knob="k", baseline_signature=baseline)
    entry = store.get(key, now_idx=0)
    assert entry is not None
    assert entry["kind"] == "enum"
    assert entry["safe_values"] == ["A"]


def test_derived_numeric_range_matches_safe_set(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("aal_core.governance.safe_set_builder.load_effects", lambda: EffectStore())

    ledger = EvidenceLedger(path=tmp_path / "ledger.jsonl")
    store = SafeSetStore(entries={})

    baseline = {"queue_depth_bucket": "<= 10"}
    for _ in range(10):
        _attempt(ledger, mid="mod", knob="k_num", value="1", baseline=baseline)
        _attempt(ledger, mid="mod", knob="k_num", value="3", baseline=baseline)

    build_safe_sets(
        ledger=ledger,
        store=store,
        tail_n=1000,
        policy={"min_attempts": 10, "safe_max_rollback_rate": 0.05, "safe_set_decay_cycles": 100},
    )

    key = safe_set_key(module_id="mod", knob="k_num", baseline_signature=baseline)
    entry = store.get(key, now_idx=0)
    assert entry is not None
    assert entry["kind"] == "numeric"
    assert entry["safe_min"] == 1.0
    assert entry["safe_max"] == 3.0


def test_decay_expiration_works():
    store = SafeSetStore(entries={})
    entry = SafeSetEntry(
        set_idx=10,
        until_idx=20,
        kind="enum",
        safe_values=["x"],
        safe_min=None,
        safe_max=None,
        support={"attempts": 10},
        provenance={},
    )
    store.set("k", entry)

    assert store.get("k", now_idx=19) is not None
    assert store.get("k", now_idx=20) is None
    assert store.prune_expired(now_idx=20) == 1
    assert store.get("k", now_idx=0) is None

