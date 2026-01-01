from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.ers.effects_store import EffectStore, record_effect, save_effects
from aal_core.governance.promotion_scanner import scan_for_promotions
from aal_core.ledger.ledger import EvidenceLedger


def test_exact_rollback_blocks_promotion():
    with TemporaryDirectory() as td:
        td_p = Path(td)
        led = EvidenceLedger(ledger_path=td_p / "ledger.jsonl", counter_path=td_p / "counter.json")

        # strong positive effect (latency down)
        base = {"queue_depth_bucket": "<= 10"}
        store = EffectStore()
        for _ in range(20):
            record_effect(
                store,
                module_id="m",
                knob="k",
                value=1,
                baseline_signature=base,
                before_metrics={"latency_ms_p95": 100.0},
                after_metrics={"latency_ms_p95": 80.0},
            )
        save_effects(store, td_p / "effects.json")

        # denominator (trial count), baseline-wide in v1.5
        led.append(entry_type="bundle_emitted", payload={"bundle": {"baseline_signature": base}}, provenance={})

        # rollback for exact (m,k,1)
        led.append(
            entry_type="rollback_emitted",
            payload={
                "rollback": {
                    "module_id": "m",
                    "baseline_signature": base,
                    "attempted_assignments": {"k": 1},
                }
            },
            provenance={},
        )

        props = scan_for_promotions(
            source_cycle_id="c",
            ledger=led,
            tail_n=100,
            policy={"min_samples": 12, "z_threshold": 2.0, "min_abs_effect": 1.0, "max_rollback_rate": 0.0},
        )
        assert props == []

