from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union


@dataclass
class RunningStats:
    """
    Deterministic running moments for scalar effects.

    Stores:
    - n: count
    - s1: sum(x)
    - s2: sum(x^2)
    """

    n: int = 0
    s1: float = 0.0
    s2: float = 0.0

    def add(self, x: float) -> None:
        self.n += 1
        self.s1 += float(x)
        self.s2 += float(x) * float(x)

    def mean(self) -> Optional[float]:
        if self.n <= 0:
            return None
        return self.s1 / self.n

    def variance(self) -> Optional[float]:
        if self.n <= 1:
            return None
        m = self.mean()
        assert m is not None
        # population variance (stable, deterministic)
        return (self.s2 / self.n) - (m * m)

    def to_dict(self) -> Dict[str, Any]:
        return {"n": self.n, "s1": self.s1, "s2": self.s2}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RunningStats":
        return RunningStats(n=int(d.get("n", 0)), s1=float(d.get("s1", 0.0)), s2=float(d.get("s2", 0.0)))


@dataclass
class EffectStore:
    """
    Bucket-aware effect stats store.

    Keys are (module, knob, value, baseline_signature, metric).
    Legacy keys (unbucketed) are still loadable but are not used when callers
    supply a baseline_signature.
    """

    stats_by_key: Dict[str, RunningStats] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"schema_version": "effect-store/0.7", "stats": {k: v.to_dict() for k, v in self.stats_by_key.items()}}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EffectStore":
        raw = d.get("stats") or {}
        out = EffectStore()
        for k, v in raw.items():
            out.stats_by_key[str(k)] = RunningStats.from_dict(v or {})
        return out


def save_effects(store: EffectStore, path: Union[str, Path]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(store.to_dict(), f, ensure_ascii=False, sort_keys=True, indent=2)


def load_effects(path: Union[str, Path]) -> EffectStore:
    p = Path(path)
    if not p.exists():
        return EffectStore()
    with p.open("r", encoding="utf-8") as f:
        d = json.load(f) or {}
    return EffectStore.from_dict(d)


def _baseline_items(baseline_sig: Dict[str, str]) -> str:
    # Stable ordering ensures determinism regardless of dict insertion order.
    return ",".join(f"{k}={baseline_sig[k]}" for k in sorted(baseline_sig))


def _k(
    module_id: str,
    knob: str,
    value: Any,
    *,
    metric_name: str,
    baseline_sig: Optional[Dict[str, str]] = None,
) -> str:
    """
    Stable, compact key.

    - Legacy (unbucketed): module::knob::value::metric
    - Bucketed (v0.7):     module::knob::value::baseline_items::metric
    """
    if baseline_sig is None:
        return f"{module_id}::{knob}::{str(value)}::{metric_name}"
    items = _baseline_items(baseline_sig)
    return f"{module_id}::{knob}::{str(value)}::{items}::{metric_name}"


def record_effect(
    store: EffectStore,
    *,
    module_id: str,
    knob: str,
    value: Any,
    baseline_signature: Dict[str, str],
    before_metrics: Dict[str, Any],
    after_metrics: Dict[str, Any],
) -> None:
    """
    Record observed deltas into (module, knob, value, baseline_bucket, metric) stats.

    Only numeric metrics present in both snapshots are recorded.
    Delta is computed as (after - before).
    """
    for metric_name, before_v in (before_metrics or {}).items():
        if metric_name not in (after_metrics or {}):
            continue
        after_v = after_metrics[metric_name]
        if not isinstance(before_v, (int, float)) or not isinstance(after_v, (int, float)):
            continue
        delta = float(after_v) - float(before_v)
        key = _k(module_id, knob, value, metric_name=metric_name, baseline_sig=baseline_signature)
        s = store.stats_by_key.get(key)
        if s is None:
            s = RunningStats()
            store.stats_by_key[key] = s
        s.add(delta)


def get_effect_stats(
    store: EffectStore,
    *,
    module_id: str,
    knob: str,
    value: Any,
    baseline_signature: Dict[str, str],
    metric_name: str,
) -> Optional[RunningStats]:
    """
    Retrieve stats for exactly the provided baseline bucket.
    """
    key = _k(module_id, knob, value, metric_name=metric_name, baseline_sig=baseline_signature)
    return store.stats_by_key.get(key)


def get_legacy_effect_stats(
    store: EffectStore,
    *,
    module_id: str,
    knob: str,
    value: Any,
    metric_name: str,
) -> Optional[RunningStats]:
    """
    Retrieve legacy (unbucketed) stats.
    Kept for backward-compatible loading / inspection only.
    """
    key = _k(module_id, knob, value, metric_name=metric_name, baseline_sig=None)
    return store.stats_by_key.get(key)

