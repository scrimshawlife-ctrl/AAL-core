# abx_runes/ram_stress.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Deque, Optional
from collections import deque


def _read_meminfo_kb() -> Optional[dict]:
    """
    Read /proc/meminfo on Linux and return key→value (kB).
    Returns None if unavailable.
    """
    try:
        data = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                rest = parts[1].strip().split()
                if not rest:
                    continue
                value_kb = int(rest[0])
                data[key] = value_kb
        return data
    except FileNotFoundError:
        return None


def compute_instant_ram_stress() -> float:
    """
    Compute a single RAM_STRESS sample in [0,1] based on MemAvailable / MemTotal.
    0.0 = no stress, 1.0 = extremely high stress.
    """
    info = _read_meminfo_kb()
    if not info:
        # If we can't introspect, assume medium stress.
        return 0.5

    total = float(info.get("MemTotal", 1))
    available = float(info.get("MemAvailable", max(1, int(total * 0.1))))

    used_fraction = 1.0 - (available / total)

    # Basic non-linear scaling: low usage → low stress, high usage → rapidly rising stress.
    if used_fraction <= 0.6:
        return used_fraction * 0.5  # keep it gentle under 60%
    elif used_fraction >= 0.95:
        return 1.0
    else:
        # smooth ramp between 0.6 and 0.95, occupying [0.3, 1.0]
        scale = (used_fraction - 0.6) / (0.95 - 0.6)
        return 0.3 + 0.7 * scale


@dataclass
class RamStressMonitor:
    """
    Maintains a sliding window of RAM_STRESS values and exposes a smoothed signal.
    """

    window_size: int = 20
    min_interval_sec: float = 0.5

    _values: Deque[float] = None  # type: ignore
    _last_update_ts: float = 0.0

    def __post_init__(self) -> None:
        self._values = deque(maxlen=self.window_size)

    @property
    def current(self) -> float:
        if not self._values:
            return compute_instant_ram_stress()
        return sum(self._values) / len(self._values)

    def sample(self, force: bool = False) -> float:
        now = time.time()
        if not force and (now - self._last_update_ts) < self.min_interval_sec and self._values:
            return self.current

        value = compute_instant_ram_stress()
        self._values.append(value)
        self._last_update_ts = now
        return self.current

    def classify(self) -> str:
        """
        Return a symbolic classification band for current RAM stress.
        """
        v = self.current
        if v < 0.25:
            return "LOW"
        elif v < 0.50:
            return "MODERATE"
        elif v < 0.75:
            return "HIGH"
        else:
            return "CRITICAL"
