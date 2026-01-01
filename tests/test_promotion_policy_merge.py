from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.governance.promotion_policy import PromotionPolicy


def test_promotion_policy_upsert_deterministic():
    with TemporaryDirectory() as td:
        path = Path(td) / "promotions.json"
        p = PromotionPolicy.load(path)
        p.upsert({"module_id": "m", "knob": "k", "value": 1, "baseline_signature": {"b": "2", "a": "1"}})
        p.upsert(
            {
                "module_id": "m",
                "knob": "k",
                "value": 1,
                "baseline_signature": {"a": "1", "b": "2"},
                "metric_name": "latency",
            }
        )
        p.save(path)
        txt = path.read_text(encoding="utf-8")
        assert '"schema_version":"promotion-policy/0.1"' in txt
        assert '"module_id":"m"' in txt

