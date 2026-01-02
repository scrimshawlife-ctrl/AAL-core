from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from .enums import ArtifactKind, LumaMode, NotComputable
from .provenance import canonical_dumps

NC = NotComputable.VALUE.value


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass(frozen=True)
class RenderArtifact:
    """
    A renderer output artifact with embedded provenance anchors.
    """

    kind: ArtifactKind
    mode: LumaMode
    scene_hash: str
    mime_type: str
    content: str  # for binary kinds, content is "not_computable" (future-ready)
    content_sha256: str
    provenance: Mapping[str, Any]
    backend: str
    warnings: Tuple[str, ...]

    @staticmethod
    def from_text(
        *,
        kind: ArtifactKind,
        mode: LumaMode,
        scene_hash: str,
        mime_type: str,
        text: str,
        provenance: Mapping[str, Any],
        backend: str,
        warnings: Tuple[str, ...] = (),
    ) -> "RenderArtifact":
        b = text.encode("utf-8")
        return RenderArtifact(
            kind=kind,
            mode=mode,
            scene_hash=scene_hash,
            mime_type=mime_type,
            content=text,
            content_sha256=_sha256_bytes(b),
            provenance=dict(provenance),
            backend=backend,
            warnings=warnings,
        )

    @staticmethod
    def not_computable(
        *,
        kind: ArtifactKind,
        mode: LumaMode,
        scene_hash: str,
        mime_type: str,
        provenance: Mapping[str, Any],
        backend: str,
        reason: str,
    ) -> "RenderArtifact":
        payload = {"not_computable": reason, "kind": kind.value, "scene_hash": scene_hash}
        return RenderArtifact(
            kind=ArtifactKind.NOT_COMPUTABLE,
            mode=mode,
            scene_hash=scene_hash,
            mime_type=mime_type,
            content=NC,
            content_sha256=hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest(),
            provenance=dict(provenance),
            backend=backend,
            warnings=(reason,),
        )
