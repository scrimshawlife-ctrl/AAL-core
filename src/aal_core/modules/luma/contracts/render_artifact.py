from dataclasses import dataclass
from typing import Any, Dict, Optional
import hashlib


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

    @property
    def content_sha256(self) -> str:
        """Alias for bytes_sha256 for backward compatibility."""
        return self.bytes_sha256

    @staticmethod
    def from_text(
        kind: Any,
        mode: Any,
        scene_hash: str,
        mime_type: str,
        text: str,
        provenance: Dict[str, Any],
        backend: str,
        warnings: tuple,
    ) -> "RenderArtifact":
        """
        Factory method to create RenderArtifact from text content.

        Args:
            kind: ArtifactKind enum value
            mode: LumaMode enum value
            scene_hash: Hash of the scene being rendered
            mime_type: MIME type (e.g., 'image/svg+xml')
            text: Text content to render
            provenance: Provenance metadata dict
            backend: Backend identifier (e.g., 'svg_static/v1')
            warnings: Tuple of warning messages

        Returns:
            RenderArtifact with computed hash and metadata
        """
        # Convert text to bytes
        payload_bytes = text.encode('utf-8')

        # Compute SHA256 hash
        bytes_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        # Determine artifact type from kind
        artifact_type_map = {
            "svg": "svg",
            "png": "png",
            "html": "html",
            "animation_plan": "animation_plan",
        }
        kind_str = str(getattr(kind, 'value', kind)).lower()
        artifact_type = artifact_type_map.get(kind_str, kind_str)

        # Generate artifact ID
        artifact_id = f"{scene_hash[:12]}:{artifact_type}:{backend}"

        # Parse backend for renderer info
        backend_parts = backend.split('/')
        renderer_id = backend_parts[0] if backend_parts else backend
        renderer_version = backend_parts[1] if len(backend_parts) > 1 else "1.0.0"

        # Convert warnings tuple to dict if needed
        warnings_dict = {"warnings": list(warnings)} if warnings else None

        return RenderArtifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            scene_hash=scene_hash,
            renderer_id=renderer_id,
            renderer_version=renderer_version,
            bytes_sha256=bytes_sha256,
            media_mime=mime_type,
            payload_bytes=payload_bytes,
            provenance=provenance,
            meta={
                "mode": str(getattr(mode, 'value', mode)),
                "backend": backend,
            },
            warnings=warnings_dict,
        )
