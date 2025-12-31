from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from abx_runes.tuning.hashing import canonical_json_dumps, sha256_hex

DEFAULT_PATH = Path(".aal/effects_store.json")


@dataclass(frozen=True)
class EffectStats:
    """
    Online mean + variance estimator per metric (Welford).

    - mean: running mean
    - m2: running sum of squares of differences from the mean (for variance)
    """

    n: int
    mean: float
    m2: float


def _update_welford(s: EffectStats, x: float) -> EffectStats:
    n2 = int(s.n) + 1
    delta = x - float(s.mean)
    mean2 = float(s.mean) + delta / n2
    delta2 = x - mean2
    m2_2 = float(s.m2) + (delta * delta2)
    return EffectStats(n=n2, mean=mean2, m2=m2_2)


def variance(s: EffectStats) -> Optional[float]:
    if int(s.n) <= 1:
        return None
    return float(s.m2) / (int(s.n) - 1)


def stderr(s: EffectStats) -> Optional[float]:
    v = variance(s)
    if v is None:
        return None
    if v <= 0.0:
        return 0.0
    return (v / int(s.n)) ** 0.5


def _key(module_id: str, knob: str, value: Any) -> str:
    """
    Deterministic (hash + canonical) key so store is stable across restarts.
    """

    canon = canonical_json_dumps({"module_id": module_id, "knob": knob, "value": value})
    h = sha256_hex(canon.encode("utf-8"))
    return f"{h}:{canon}"


@dataclass
class EffectStore:
    """
    stats[key][metric_name] = EffectStats
    """

    stats: Dict[str, Dict[str, EffectStats]]

    def to_jsonable(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, m in (self.stats or {}).items():
            out[str(key)] = {
                str(mn): {"n": int(st.n), "mean": float(st.mean), "m2": float(st.m2)} for mn, st in (m or {}).items()
            }
        return out

    @staticmethod
    def from_jsonable(d: Dict[str, Any]) -> "EffectStore":
        stats: Dict[str, Dict[str, EffectStats]] = {}
        for key, m in (d or {}).items():
            mm: Dict[str, EffectStats] = {}
            for mn, st in (m or {}).items():
                try:
                    mm[str(mn)] = EffectStats(
                        n=int(st["n"]),
                        mean=float(st["mean"]),
                        # backward-compatible: if m2 missing, treat as 0.0
                        m2=float(st.get("m2", 0.0)),
                    )
                except Exception:
                    continue
            if mm:
                stats[str(key)] = mm
        return EffectStore(stats=stats)


def load_effects(path: Path = DEFAULT_PATH) -> EffectStore:
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return EffectStore(stats={})
    except Exception:
        return EffectStore(stats={})

    # Back-compat: older stores may have been just the jsonable stats dict.
    if isinstance(d, dict) and "store" in d and isinstance(d["store"], dict):
        return EffectStore.from_jsonable(d["store"])
    if isinstance(d, dict):
        return EffectStore.from_jsonable(d)
    return EffectStore(stats={})


def save_effects(store: EffectStore, path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "effects-store/0.6",
        "store": store.to_jsonable(),
    }
    payload["store_hash"] = sha256_hex(canonical_json_dumps(payload["store"]).encode("utf-8"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(canonical_json_dumps(payload) + "\n")


def record_effect(
    store: EffectStore,
    *,
    module_id: str,
    knob: str,
    value: Any,
    before_metrics: Dict[str, Any],
    after_metrics: Dict[str, Any],
    metric_names: Optional[list[str]] = None,
) -> None:
    """
    Record observed deltas: (after - before) per metric.
    Deterministic, online update.
    """

    def _f(x: Any) -> Optional[float]:
        if x is None:
            return None
        try:
            return float(x)
        except Exception:
            return None

    if metric_names is None:
        metric_names = sorted(set((before_metrics or {}).keys()) | set((after_metrics or {}).keys()))

    k = _key(str(module_id), str(knob), value)
    mm = store.stats.get(k)
    if mm is None:
        mm = {}
        store.stats[k] = mm

    for mn in metric_names:
        b = _f((before_metrics or {}).get(mn))
        a = _f((after_metrics or {}).get(mn))
        if b is None or a is None:
            continue
        delta = float(a - b)
        st = mm.get(mn) or EffectStats(n=0, mean=0.0, m2=0.0)
        mm[mn] = _update_welford(st, delta)


def get_effect_stats(
    store: EffectStore, *, module_id: str, knob: str, value: Any, metric_name: str
) -> Optional[EffectStats]:
    k = _key(str(module_id), str(knob), value)
    mm = (store.stats or {}).get(k)
    if not mm:
        return None
    return mm.get(metric_name)


# Back-compat alias (v0.5 naming)
def get_effect_mean(
    store: EffectStore, *, module_id: str, knob: str, value: Any, metric_name: str
) -> Optional[EffectStats]:
    return get_effect_stats(store, module_id=module_id, knob=knob, value=value, metric_name=metric_name)

