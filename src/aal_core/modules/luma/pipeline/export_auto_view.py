from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib
import json
from typing import Any, Dict

from ..contracts.auto_view_ir import AutoViewPlan


def export_auto_view_plan(
    plan: AutoViewPlan, out_dir: str, scene_id: str
) -> Dict[str, Any]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        asdict(plan), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    path = str(Path(out_dir) / f"{scene_id}:{sha[:12]}:auto_view_plan.json")
    Path(path).write_bytes(payload)
    return {"path": path, "bytes_sha256": sha, "view_id": plan.view_id}
