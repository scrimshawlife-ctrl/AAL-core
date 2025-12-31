from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from abx_runes.tuning.hashing import canonical_json_dumps, sha256_hex
from .stabilization import StabilizationState


DEFAULT_PATH = Path(".aal/stabilization_state.json")


def _encode_key(k: Tuple[str, str]) -> str:
    return f"{k[0]}::{k[1]}"


def _decode_key(s: str) -> Tuple[str, str]:
    a, b = s.split("::", 1)
    return (a, b)


def save_state(state: StabilizationState, path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "stabilization-state/0.1",
        "content_hash": "",
        "cycles_since_change": { _encode_key(k): int(v) for k, v in state.cycles_since_change.items() },
    }
    payload["content_hash"] = sha256_hex(canonical_json_dumps({**payload, "content_hash": ""}).encode("utf-8"))
    path.write_text(canonical_json_dumps(payload) + "\n", encoding="utf-8")


def load_state(path: Path = DEFAULT_PATH) -> StabilizationState:
    if not path.exists():
        return StabilizationState(cycles_since_change={})
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema_version") != "stabilization-state/0.1":
        return StabilizationState(cycles_since_change={})
    # verify hash (best-effort; if mismatch, treat as empty)
    claimed = str(d.get("content_hash", ""))
    tmp = dict(d)
    tmp["content_hash"] = ""
    actual = sha256_hex(canonical_json_dumps(tmp).encode("utf-8"))
    if claimed and claimed != actual:
        return StabilizationState(cycles_since_change={})
    raw: Dict[str, int] = d.get("cycles_since_change", {}) or {}
    out: Dict[Tuple[str, str], int] = {}
    for k, v in raw.items():
        try:
            out[_decode_key(k)] = int(v)
        except Exception:
            continue
    return StabilizationState(cycles_since_change=out)
