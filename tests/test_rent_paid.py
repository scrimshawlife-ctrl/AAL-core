from aal_core.ers.rent import RentThresholds, rent_paid


def test_rent_paid_ok():
    before = {"latency_ms_p95": 120.0, "cost_units": 2.0, "error_rate": 0.02, "throughput_per_s": 10.0}
    after  = {"latency_ms_p95": 90.0,  "cost_units": 1.5, "error_rate": 0.01, "throughput_per_s": 12.0}
    th = RentThresholds(max_latency_ms_p95=100.0, max_cost_units=2.0, max_error_rate=0.02, min_throughput_per_s=11.0)
    ok, reason = rent_paid(before, after, th)
    assert ok is True, reason


def test_rent_paid_fails_latency():
    before = {"latency_ms_p95": 120.0}
    after  = {"latency_ms_p95": 150.0}
    th = RentThresholds(max_latency_ms_p95=100.0)
    ok, reason = rent_paid(before, after, th)
    assert ok is False
    assert reason == "latency_fail"
