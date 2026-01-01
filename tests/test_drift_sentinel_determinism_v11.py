from aal_core.ers.drift_sentinel import compute_drift


def test_drift_sentinel_deterministic():
    prev = {"latency_ms_p95": 100.0, "error_rate": 0.01, "cost_units": 10.0, "throughput_per_s": 100.0}
    now = {"latency_ms_p95": 140.0, "error_rate": 0.03, "cost_units": 12.5, "throughput_per_s": 70.0}

    d1 = compute_drift(prev_metrics=prev, now_metrics=now)
    d2 = compute_drift(prev_metrics=prev, now_metrics=now)

    assert d1 == d2
    assert 0.0 <= d1.drift_score <= 1.0

