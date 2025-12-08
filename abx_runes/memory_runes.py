# abx_runes/memory_runes.py

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


class Volatility(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class MemoryTier(str, Enum):
    LOCAL = "LOCAL"      # DRAM / closest memory
    EXTENDED = "EXTENDED"  # CXL / NVMe-backed, slower
    COLD = "COLD"        # disk / object store


class KvPolicy(str, Enum):
    LRU = "LRU"
    WINDOW = "WINDOW"
    TASK_BOUND = "TASK_BOUND"


@dataclass(frozen=True)
class MemRune:
    soft_cap_mb: int
    hard_cap_mb: int
    volatility: Volatility

    def validate(self) -> None:
        if self.soft_cap_mb <= 0:
            raise ValueError("soft_cap_mb must be > 0")
        if self.hard_cap_mb < self.soft_cap_mb:
            raise ValueError("hard_cap_mb must be >= soft_cap_mb")


@dataclass(frozen=True)
class KvRune:
    cap_fraction: float  # fraction of total RAM allowed for KV cache
    policy: KvPolicy
    purge_on_stress: bool
    purge_on_event: bool

    def validate(self) -> None:
        if not (0.0 < self.cap_fraction <= 1.0):
            raise ValueError("cap_fraction must be in (0, 1]")


@dataclass(frozen=True)
class DegradeStep:
    order: int
    action: str
    args: Tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        arg_str = ",".join(self.args)
        return f"STEP{self.order}:{self.action}({arg_str})" if self.args else f"STEP{self.order}:{self.action}"


@dataclass(frozen=True)
class DegradePath:
    steps: List[DegradeStep]

    def sorted_steps(self) -> List[DegradeStep]:
        return sorted(self.steps, key=lambda s: s.order)


@dataclass(frozen=True)
class MemoryProfile:
    """
    Complete memory contract for a module / pipeline.
    """
    mem: MemRune
    kv: Optional[KvRune]
    tier: MemoryTier
    priority: int  # 0 (lowest) - 9 (highest)
    degrade: Optional[DegradePath]

    def validate(self) -> None:
        self.mem.validate()
        if self.kv:
            self.kv.validate()
        if not (0 <= self.priority <= 9):
            raise ValueError("priority must be in [0, 9]")


# --- Parsing layer -----------------------------------------------------------

_MEM_RE = re.compile(
    r"MEM\[\s*SOFT=(?P<soft>\d+)\s*,\s*HARD=(?P<hard>\d+)\s*,\s*VOL=(?P<vol>LOW|MED|HIGH)\s*\]"
)

_KV_RE = re.compile(
    r"KV\[\s*CAP=(?P<cap>[0-1](?:\.\d+)?)\s*,\s*POLICY=(?P<policy>LRU|WINDOW|TASK_BOUND)\s*,\s*PURGE=(?P<purge>[A-Z_]+)\s*\]"
)

_TIER_RE = re.compile(
    r"TIER=(?P<tier>LOCAL|EXTENDED|COLD)"
)

_PRIORITY_RE = re.compile(
    r"PRIORITY=(?P<priority>[0-9])"
)

_DEGRADE_STEP_RE = re.compile(
    r"STEP(?P<idx>\d+)\s*:\s*(?P<action>[A-Z_]+)(?:\((?P<args>[^)]*)\))?"
)


def parse_mem_rune(text: str) -> MemRune:
    m = _MEM_RE.search(text)
    if not m:
        raise ValueError(f"MEM rune not found in: {text!r}")
    soft = int(m.group("soft"))
    hard = int(m.group("hard"))
    vol = Volatility(m.group("vol"))
    rune = MemRune(soft_cap_mb=soft, hard_cap_mb=hard, volatility=vol)
    rune.validate()
    return rune


def parse_kv_rune(text: str) -> Optional[KvRune]:
    m = _KV_RE.search(text)
    if not m:
        return None
    cap = float(m.group("cap"))
    policy = KvPolicy(m.group("policy"))
    purge = m.group("purge")
    purge_on_stress = purge in ("ON_STRESS", "ON_STRESS_OR_EVENT")
    purge_on_event = purge in ("ON_EVENT", "ON_STRESS_OR_EVENT")
    rune = KvRune(
        cap_fraction=cap,
        policy=policy,
        purge_on_stress=purge_on_stress,
        purge_on_event=purge_on_event,
    )
    rune.validate()
    return rune


def parse_tier_rune(text: str) -> MemoryTier:
    m = _TIER_RE.search(text)
    if not m:
        # default to LOCAL if not specified
        return MemoryTier.LOCAL
    return MemoryTier(m.group("tier"))


def parse_priority_rune(text: str) -> int:
    m = _PRIORITY_RE.search(text)
    if not m:
        # default mid priority
        return 5
    return int(m.group("priority"))


def parse_degrade_rune(text: str) -> Optional[DegradePath]:
    if "DEGRADE{" not in text:
        return None
    inner = text.split("DEGRADE{", 1)[1].rsplit("}", 1)[0]
    steps: List[DegradeStep] = []
    for match in _DEGRADE_STEP_RE.finditer(inner):
        idx = int(match.group("idx"))
        action = match.group("action")
        args_raw = match.group("args")
        args = tuple(a.strip() for a in args_raw.split(",") if a.strip()) if args_raw else ()
        steps.append(DegradeStep(order=idx, action=action, args=args))
    return DegradePath(steps=steps) if steps else None


def parse_memory_profile(text: str) -> MemoryProfile:
    """
    Parse a full runic annotation block into a MemoryProfile.

    Example input:

        MEM[SOFT=2048,HARD=4096,VOL=MED];
        KV[CAP=0.2,POLICY=WINDOW,PURGE=ON_STRESS];
        TIER=EXTENDED;
        PRIORITY=7;
        DEGRADE{
          STEP1:SHRINK_KV(0.75),
          STEP2:CONTEXT(4096),
          STEP3:DISABLE(HIGH_COST_METRICS),
          STEP4:BATCH(ASYNC),
          STEP5:OFFLOAD(EXTENDED)
        }

    """
    mem = parse_mem_rune(text)
    kv = parse_kv_rune(text)
    tier = parse_tier_rune(text)
    priority = parse_priority_rune(text)
    degrade = parse_degrade_rune(text)
    profile = MemoryProfile(mem=mem, kv=kv, tier=tier, priority=priority, degrade=degrade)
    profile.validate()
    return profile
