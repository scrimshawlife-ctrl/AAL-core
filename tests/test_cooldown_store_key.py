from aal_core.ers.cooldown import cooldown_key


def test_cooldown_key_stable() -> None:
    sig = {"b": "2", "a": "1"}
    k1 = cooldown_key(module_id="m", knob="k", value=1, baseline_signature=sig)
    k2 = cooldown_key(module_id="m", knob="k", value=1, baseline_signature={"a": "1", "b": "2"})
    assert k1 == k2

