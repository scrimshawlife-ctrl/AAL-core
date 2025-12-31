from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from abx_runes.tuning.hashing import canonical_json_dumps, sha256_hex


DEFAULT_PATH = Path(".aal/effects_store.json")


def _k(module_id: str, knob: str, value: Any) -> str:
    return f"{module_id}::{knob}::{str(value)}"


@dataclass(frozen=True)
class EffectStats:
    """
    Online mean estimator per metric (cheap + deterministic for v0.5).
    """

    n: int
    mean: float


def _update_mean(s: EffectStats, x: float) -> EffectStats:
    n2 = s.n + 1
    mean2 = s.mean + (x - s.mean) / n2
    return EffectStats(n=n2, mean=mean2)


@dataclass
class EffectStore:
    """
    Maps (module, knob, value) -> per-metric EffectStats for observed deltas:
      delta = after - before
    """

    stats: Dict[str, Dict[str, EffectStats]]  # key -> metric_name -> stats

    def to_jsonable(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, m in self.stats.items():
            out[key] = {mn: {"n": st.n, "mean": st.mean} for mn, st in m.items()}
        return out

    @staticmethod
    def from_jsonable(d: Dict[str, Any]) -> "EffectStore":
        stats: Dict[str, Dict[str, EffectStats]] = {}
        for key, m in (d or {}).items():
            mm: Dict[str, EffectStats] = {}
            for mn, st in (m or {}).items():
                try:
                    mm[mn] = EffectStats(n=int(st["n"]), mean=float(st["mean"]))
                except Exception:
                    continue
            if mm:
                stats[str(key)] = mm
        return EffectStore(stats=stats)


def load_effects(path: Path = DEFAULT_PATH) -> EffectStore:
    if not path.exists():
        return EffectStore(stats={})
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema_version") != "effects-store/0.1":
        return EffectStore(stats={})
    claimed = str(d.get("content_hash", ""))
    tmp = dict(d)
    tmp["content_hash"] = ""
    actual = sha256_hex(canonical_json_dumps(tmp).encode("utf-8"))
    if claimed and claimed != actual:
        return EffectStore(stats={})
    return EffectStore.from_jsonable(d.get("stats", {}) or {})


def save_effects(store: EffectStore, path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "schema_version": "effects-store/0.1",
        "content_hash": "",
        "stats": store.to_jsonable(),
    }
    payload["content_hash"] = sha256_hex(
        canonical_json_dumps({**payload, "content_hash": ""}).encode("utf-8")
    )
    path.write_text(canonical_json_dumps(payload) + "\n", encoding="utf-8")


def record_effect(
    store: EffectStore,
    *,
    module_id: str,
    knob: str,
    value: Any,
    before_metrics: Dict[str, Any],
    after_metrics: Dict[str, Any],
    metric_names: Tuple[str, ...] = (
        "latency_ms_p95",
        "cost_units",
        "error_rate",
        "throughput_per_s",
    ),
) -> None:
    key = _k(module_id, knob, value)
    if key not in store.stats:
        store.stats[key] = {}
    mm = store.stats[key]

    def _f(x: Any) -> Optional[float]:
        try:
            return float(x)
        except Exception:
            return None

    for mn in metric_names:
        b = _f(before_metrics.get(mn))
        a = _f(after_metrics.get(mn))
        if b is None or a is None:
            continue
        delta = a - b
        st = mm.get(mn) or EffectStats(n=0, mean=0.0)
        mm[mn] = _update_mean(st, float(delta))


def get_effect_mean(
    store: EffectStore,
    *,
    module_id: str,
    knob: str,
    value: Any,
    metric_name: str,
) -> Optional[EffectStats]:
    key = _k(module_id, knob, value)
    mm = store.stats.get(key)
    if not mm:
        return None
    return mm.get(metric_name)

