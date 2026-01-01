from aal_core.runtime.promotion_overlay import PromotionOverlay
from aal_core.runtime.promotion_report import build_promotion_report


def test_report_no_promotions():
    overlay = PromotionOverlay(by_module_and_base={}, bias_weight=0.2)
    r = build_promotion_report(
        module_id="m",
        baseline_signature={},
        candidates=[{"knob": "k", "value": 1}],
        selected=[{"knob": "k", "value": 1}],
        overlay=overlay,
        promotion_bias_weight=0.2,
    )
    assert r["candidates_with_promotion_available"] == 0
    assert r["selected_with_promotion"] == 0

