from __future__ import annotations

from pathlib import Path
import hashlib
import json
from typing import Dict

from ..contracts.scene_ir import LumaSceneIR


def export_scene_ir(scene: LumaSceneIR, out_dir: str) -> Dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    payload = scene.to_canonical_dict(include_hash=True)
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    path = str(Path(out_dir) / f"{scene.scene_id}:{sha[:12]}:scene_ir.json")
    with open(path, "wb") as f:
        f.write(data)
    return {"path": path, "bytes_sha256": sha}
