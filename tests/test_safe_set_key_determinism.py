from aal_core.ers.safe_set_store import safe_set_key


def test_safe_set_key_sorted_baseline():
    k1 = safe_set_key(module_id="m", knob="k", baseline_signature={"b": "2", "a": "1"})
    k2 = safe_set_key(module_id="m", knob="k", baseline_signature={"a": "1", "b": "2"})
    assert k1 == k2

