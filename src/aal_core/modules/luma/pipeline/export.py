from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from ..contracts.render_artifact import RenderArtifact


@dataclass(frozen=True)
class ExportResult:
    path: str
    bytes_sha256: str
    size_bytes: int


def export_artifact(artifact: RenderArtifact, out_dir: str) -> ExportResult:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ext = {
        "svg": ".svg",
        "png": ".png",
        "html": ".html",
        "animation_plan": ".json",
    }.get(artifact.artifact_type, ".bin")

    filename = f"{artifact.artifact_id.replace(':','_')}{ext}"
    path = str(Path(out_dir) / filename)

    with open(path, "wb") as f:
        f.write(artifact.payload_bytes)

    sha = hashlib.sha256(artifact.payload_bytes).hexdigest()
    if sha != artifact.bytes_sha256:
        raise ValueError("artifact bytes sha mismatch (provenance violation)")

    return ExportResult(path=path, bytes_sha256=sha, size_bytes=len(artifact.payload_bytes))
