from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.ers.effects_store import load_effects, save_effects, record_effect, get_effect_stats, variance, stderr


def test_effects_store_roundtrip_and_update_mean():
    with TemporaryDirectory() as td:
        p = Path(td) / "effects_store.json"
        store = load_effects(p)

        # latency delta is after - before (negative is good)
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
        st = get_effect_stats(store2, module_id="m", knob="k", value=1, metric_name="latency_ms_p95")
        assert st is not None
        assert st.n == 2
        assert abs(st.mean - (-10.0)) < 1e-6
        v = variance(st)
        se = stderr(st)
        assert v is not None
        assert se is not None

