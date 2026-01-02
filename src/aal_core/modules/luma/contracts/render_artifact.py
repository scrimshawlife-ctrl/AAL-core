from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RenderArtifact:
    artifact_id: str
    artifact_type: str  # "svg" | "png" | "html" | "animation_plan"
    scene_hash: str
    renderer_id: str
    renderer_version: str
    bytes_sha256: str
    media_mime: str
    payload_bytes: bytes
    provenance: Dict[str, Any]
    meta: Dict[str, Any]
    warnings: Optional[Dict[str, Any]] = None
