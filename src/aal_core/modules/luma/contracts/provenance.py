from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


def _as_jsonable(x: Any) -> Any:
    """
    Convert common Python objects into JSON-stable representations.

    This is intentionally conservative: if a value cannot be represented,
    represent it as a deterministic string marker.
    """

    if x is None:
        return None
    if isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, bytes):
        return {"__bytes__": hashlib.sha256(x).hexdigest()}
    if isinstance(x, Mapping):
        return {str(k): _as_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_as_jsonable(v) for v in x]
    if hasattr(x, "model_dump"):  # pydantic v2
        return _as_jsonable(x.model_dump())
    if hasattr(x, "dict"):  # pydantic v1-ish compatibility
        return _as_jsonable(x.dict())
    return {"__unjsonable__": f"{type(x).__module__}.{type(x).__qualname__}"}


def canonical_dumps(obj: Any) -> str:
    """
    Canonical JSON serialization for hashing.

    - sorted keys
    - compact separators
    - no NaN / Infinity
    """

    return json.dumps(
        _as_jsonable(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_dumps(obj).encode("utf-8")).hexdigest()


def _dig(d: Mapping[str, Any], path: Sequence[str]) -> Optional[Any]:
    cur: Any = d
    for p in path:
        if not isinstance(cur, Mapping) or p not in cur:
            return None
        cur = cur[p]
    return cur


@dataclass(frozen=True)
class SourceFrameProvenance:
    """
    Deterministic provenance anchors derived from a ResonanceFrame.
    """

    module: str
    utc: str
    payload_sha256: str
    vendor_lock_sha256: str
    manifest_sha256: str
    abx_runes_used: Tuple[str, ...]
    abx_runes_gate_state: str

    @staticmethod
    def from_resonance_frame(frame: Any) -> "SourceFrameProvenance":
        """
        Accept either:
        - `aal_core.schema.resonance_frame.ResonanceFrame` (TypedDict-like)
        - `aal_core.models.ResonanceFrame` (pydantic model)
        - or any mapping with the same key shape.
        """

        if hasattr(frame, "model_dump"):
            f: Dict[str, Any] = frame.model_dump()
        elif isinstance(frame, Mapping):
            f = dict(frame)
        else:
            raise TypeError(f"Unsupported frame type: {type(frame)!r}")

        module = str(f.get("module") or f.get("source") or "not_computable")
        utc = str(f.get("utc") or f.get("timestamp") or "not_computable")

        payload = f.get("payload")
        if payload is None:
            # pydantic model uses a different shape; treat the whole model as payload
            payload = f.get("attachments") or {}
        payload_sha256 = sha256_hex(payload)

        prov = f.get("provenance") or {}
        vendor_lock_sha256 = str(prov.get("vendor_lock_sha256") or "not_computable")
        manifest_sha256 = str(prov.get("manifest_sha256") or "not_computable")

        abx = f.get("abx_runes") or {}
        used = abx.get("used") or ()
        if isinstance(used, list):
            used_t = tuple(str(x) for x in used)
        elif isinstance(used, tuple):
            used_t = tuple(str(x) for x in used)
        else:
            used_t = tuple()
        used_t = tuple(sorted(used_t))
        gate_state = str(abx.get("gate_state") or "not_computable")

        return SourceFrameProvenance(
            module=module,
            utc=utc,
            payload_sha256=payload_sha256,
            vendor_lock_sha256=vendor_lock_sha256,
            manifest_sha256=manifest_sha256,
            abx_runes_used=used_t,
            abx_runes_gate_state=gate_state,
        )


def stable_scene_seed(frame_prov: SourceFrameProvenance) -> int:
    """
    Derive a stable integer seed for deterministic layout jitter/rotation.

    Canonical law: same input -> same IR -> same render.
    """

    h = hashlib.sha256(
        canonical_dumps(
            {
                "module": frame_prov.module,
                "utc": frame_prov.utc,
                "payload_sha256": frame_prov.payload_sha256,
                "vendor_lock_sha256": frame_prov.vendor_lock_sha256,
                "manifest_sha256": frame_prov.manifest_sha256,
                "abx_runes_used": frame_prov.abx_runes_used,
                "abx_runes_gate_state": frame_prov.abx_runes_gate_state,
            }
        ).encode("utf-8")
    ).digest()
    return int.from_bytes(h[:8], byteorder="big", signed=False)
