from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.ers.effects_store import get_effect_mean, load_effects, record_effect, save_effects


def test_effects_store_roundtrip_and_update_mean():
    with TemporaryDirectory() as td:
        p = Path(td) / "effects.json"
        store = load_effects(p)
        record_effect(
            store,
            module_id="m",
            knob="k",
            value=1,
            before_metrics={"latency_ms_p95": 100.0},
            after_metrics={"latency_ms_p95": 90.0},
        )
        record_effect(
            store,
            module_id="m",
            knob="k",
            value=1,
            before_metrics={"latency_ms_p95": 90.0},
            after_metrics={"latency_ms_p95": 80.0},
        )
        save_effects(store, p)
        store2 = load_effects(p)
        st = get_effect_mean(store2, module_id="m", knob="k", value=1, metric_name="latency_ms_p95")
        assert st is not None
        assert st.n == 2
        assert abs(st.mean - (-10.0)) < 1e-6

