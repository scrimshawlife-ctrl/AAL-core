# tests/test_memory_runes.py

from abx_runes.memory_runes import (
    parse_mem_rune,
    parse_kv_rune,
    parse_memory_profile,
    Volatility,
    MemoryTier,
)
from abx_runes.ram_stress import compute_instant_ram_stress


def test_parse_mem_rune_basic():
    text = "MEM[SOFT=1024,HARD=2048,VOL=MED]"
    mem = parse_mem_rune(text)
    assert mem.soft_cap_mb == 1024
    assert mem.hard_cap_mb == 2048
    assert mem.volatility is Volatility.MED


def test_parse_kv_rune_basic():
    text = "KV[CAP=0.2,POLICY=WINDOW,PURGE=ON_STRESS]"
    kv = parse_kv_rune(text)
    assert kv is not None
    assert abs(kv.cap_fraction - 0.2) < 1e-6
    assert kv.policy.value == "WINDOW"
    assert kv.purge_on_stress is True
    assert kv.purge_on_event is False


def test_parse_full_profile():
    text = """
    MEM[SOFT=2048,HARD=4096,VOL=LOW];
    KV[CAP=0.3,POLICY=LRU,PURGE=ON_STRESS_OR_EVENT];
    TIER=EXTENDED;
    PRIORITY=8;
    DEGRADE{
      STEP1:SHRINK_KV(0.75),
      STEP2:CONTEXT(4096),
      STEP3:DISABLE(HIGH_COST_METRICS),
      STEP4:BATCH(ASYNC),
      STEP5:OFFLOAD(EXTENDED)
    }
    """
    profile = parse_memory_profile(text)
    assert profile.mem.soft_cap_mb == 2048
    assert profile.tier is MemoryTier.EXTENDED
    assert profile.priority == 8
    assert profile.degrade is not None
    assert len(profile.degrade.steps) == 5


def test_ram_stress_range():
    value = compute_instant_ram_stress()
    assert 0.0 <= value <= 1.0
