from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.ers.effects_store import EffectStore, record_effect, save_effects
from aal_core.governance.promotion_scanner import scan_for_promotions
from aal_core.ledger.ledger import EvidenceLedger


def test_promotion_scan_deterministic():
    with TemporaryDirectory() as td:
        td = Path(td)
        led = EvidenceLedger(ledger_path=td / "ledger.jsonl", counter_path=td / "counter.json")
        effects_path = td / "effects.json"

        store = EffectStore()
        base = {"queue_depth_bucket": "<= 10"}
        for _ in range(20):
            record_effect(
                store,
                module_id="m",
                knob="k",
                value=1,
                baseline_signature=base,
                before_metrics={"latency_ms_p95": 100.0},
                after_metrics={"latency_ms_p95": 90.0},
            )
        save_effects(store, effects_path)

        led.append(entry_type="bundle_emitted", payload={"bundle": {"baseline_signature": base}}, provenance={})

        policy = {"min_samples": 12, "z_threshold": 2.0, "min_abs_effect": 1.0, "metrics": ["latency_ms_p95"]}
        p1 = scan_for_promotions(source_cycle_id="c", ledger=led, tail_n=100, policy=policy, effects_path=str(effects_path))
        p2 = scan_for_promotions(source_cycle_id="c", ledger=led, tail_n=100, policy=policy, effects_path=str(effects_path))
        assert p1 == p2

