from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.ers.effects_store import EffectStore, record_effect, save_effects
from aal_core.governance.promotion_scanner import scan_for_promotions
from aal_core.ledger.ledger import EvidenceLedger


def test_gate_min_abs_effect_blocks_promotion():
    with TemporaryDirectory() as td:
        td = Path(td)
        led = EvidenceLedger(ledger_path=td / "ledger.jsonl", counter_path=td / "counter.json")
        effects_path = td / "effects.json"

        store = EffectStore()
        base = {"queue_depth_bucket": "<= 10"}
        # 6x 0.0 and 6x 1.0 => mean 0.5, var > 0, z can be high
        for _ in range(6):
            record_effect(
                store,
                module_id="m",
                knob="k",
                value=1,
                baseline_signature=base,
                before_metrics={"latency_ms_p95": 100.0},
                after_metrics={"latency_ms_p95": 100.0},
            )
        for _ in range(6):
            record_effect(
                store,
                module_id="m",
                knob="k",
                value=1,
                baseline_signature=base,
                before_metrics={"latency_ms_p95": 100.0},
                after_metrics={"latency_ms_p95": 101.0},
            )
        save_effects(store, effects_path)

        led.append(entry_type="bundle_emitted", payload={"bundle": {"baseline_signature": base}}, provenance={})

        policy = {"min_samples": 12, "z_threshold": 2.0, "min_abs_effect": 1.0, "metrics": ["latency_ms_p95"]}
        proposals = scan_for_promotions(source_cycle_id="c", ledger=led, tail_n=100, policy=policy, effects_path=str(effects_path))
        assert proposals == []


def test_gate_rollback_rate_blocks_promotion():
    with TemporaryDirectory() as td:
        td = Path(td)
        led = EvidenceLedger(ledger_path=td / "ledger.jsonl", counter_path=td / "counter.json")
        effects_path = td / "effects.json"

        store = EffectStore()
        base = {"queue_depth_bucket": "<= 10"}
        # Strong, consistent effect (delta -10)
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

        # trial opportunities (denominator)
        for _ in range(5):
            led.append(entry_type="bundle_emitted", payload={"bundle": {"baseline_signature": base}}, provenance={})
        # rollbacks (numerator)
        for _ in range(2):
            led.append(
                entry_type="rollback_emitted",
                payload={"rollback": {"module_id": "m", "baseline_signature": base}},
                provenance={},
            )

        policy = {
            "min_samples": 12,
            "z_threshold": 2.0,
            "min_abs_effect": 1.0,
            "max_rollback_rate": 0.10,
            "metrics": ["latency_ms_p95"],
        }
        proposals = scan_for_promotions(source_cycle_id="c", ledger=led, tail_n=100, policy=policy, effects_path=str(effects_path))
        assert proposals == []

