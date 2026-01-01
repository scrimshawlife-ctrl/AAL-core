from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

from aal_core.ers.effects_store import EffectStore
from aal_core.governance.promotion_executor import apply_approved_promotions
from aal_core.governance.promotion_policy import PromotionPolicy
from aal_core.ledger.ledger import EvidenceLedger


@dataclass
class _Desc:
    tuning_envelope: Dict[str, Any]
    capability: Any
    stabilization_state: Any = None


class _Registry:
    def __init__(self, envelope: Dict[str, Any], capability: Any):
        self._desc = _Desc(tuning_envelope=envelope, capability=capability)

    def get_module_descriptor(self, module_id: str) -> _Desc:
        return self._desc


class _Cap:
    # CapabilityToken is checked structurally in ers/tuning_apply.py via can_apply();
    # for this test we avoid any required capability by leaving specs empty.
    pass


def _envelope_for_knob(knob_name: str) -> Dict[str, Any]:
    return {
        "schema_version": "tuning-envelope/0.1",
        "knobs": [
            {
                "name": knob_name,
                "type": "int",
                "min": 0,
                "max": 1000,
                "hot_apply": True,
                "capability_required": "",
                "stabilization_cycles": 0,
            }
        ],
    }


def test_apply_promotion_writes_ledger_events():
    with TemporaryDirectory() as td:
        td_path = Path(td)
        promotions_path = td_path / "promotions.json"
        ledger_path = td_path / "ledger.jsonl"

        assignments: Dict[str, Any] = {"k": 0}
        metrics: List[Dict[str, Any]] = [
            {"latency_ms_p95": 100.0, "queue_depth": 1, "input_size": 10},
            {"latency_ms_p95": 99.0, "queue_depth": 1, "input_size": 10},
        ]

        def get_metrics_snapshot() -> Dict[str, Any]:
            return metrics.pop(0) if metrics else {"latency_ms_p95": 99.0}

        def get_current_assignments(module_id: str) -> Dict[str, Any]:
            return assignments

        registry = _Registry(_envelope_for_knob("k"), _Cap())
        effects = EffectStore()

        res = apply_approved_promotions(
            approved_proposals=[
                {
                    "proposal_hash": "ph1",
                    "metric_name": "latency_ms_p95",
                    "baseline_signature": {"mode": "x"},
                    "target": {"module_id": "m1", "knob_name": "k", "value": 1},
                }
            ],
            registry=registry,
            effects_store=effects,
            get_metrics_snapshot=get_metrics_snapshot,
            get_current_assignments=get_current_assignments,
            policy={"canary_max_abs_delta": 0.0, "canary_max_rel_delta": 0.0},
            promotions_path=promotions_path,
            ledger_path=ledger_path,
        )

        assert res["applied"]
        ledger = EvidenceLedger(path=ledger_path)
        tail = ledger.read_tail(3)
        types = [e["entry_type"] for e in tail]
        assert "promotion_applied" in types
        assert "promotion_canary_ok" in types

        prom = PromotionPolicy.load(promotions_path)
        assert len(prom.items) == 1
        assert prom.items[0]["proposal_hash"] == "ph1"


def test_failing_canary_revokes_existing_promotion():
    with TemporaryDirectory() as td:
        td_path = Path(td)
        promotions_path = td_path / "promotions.json"
        ledger_path = td_path / "ledger.jsonl"

        # Seed an existing promotion (so rollback can "revoke" it).
        pp = PromotionPolicy(items=[])
        pp.upsert(
            {
                "module_id": "m1",
                "knob": "k",
                "value": 1,
                "baseline_signature": {"mode": "x"},
                "metric_name": "latency_ms_p95",
                "promoted_at_idx": 0,
                "proposal_hash": "ph1",
            }
        )
        pp.save(promotions_path)

        assignments: Dict[str, Any] = {"k": 0}
        metrics: List[Dict[str, Any]] = [
            {"latency_ms_p95": 100.0, "queue_depth": 1, "input_size": 10},
            {"latency_ms_p95": 120.0, "queue_depth": 1, "input_size": 10},  # worse
        ]

        def get_metrics_snapshot() -> Dict[str, Any]:
            return metrics.pop(0) if metrics else {"latency_ms_p95": 120.0}

        def get_current_assignments(module_id: str) -> Dict[str, Any]:
            return assignments

        registry = _Registry(_envelope_for_knob("k"), _Cap())
        effects = EffectStore()

        res = apply_approved_promotions(
            approved_proposals=[
                {
                    "proposal_hash": "ph1",
                    "metric_name": "latency_ms_p95",
                    "baseline_signature": {"mode": "x"},
                    "target": {"module_id": "m1", "knob_name": "k", "value": 1},
                }
            ],
            registry=registry,
            effects_store=effects,
            get_metrics_snapshot=get_metrics_snapshot,
            get_current_assignments=get_current_assignments,
            policy={"canary_max_abs_delta": 1.0, "canary_max_rel_delta": 0.01},
            promotions_path=promotions_path,
            ledger_path=ledger_path,
        )

        assert res["rolled_back"]

        prom = PromotionPolicy.load(promotions_path)
        assert prom.items[0].get("revoked_at_idx") is not None

        ledger = EvidenceLedger(path=ledger_path)
        tail = ledger.read_tail(5)
        assert any(e["entry_type"] == "promotion_rolled_back" for e in tail)

