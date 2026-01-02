from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib
import json
from typing import Any, Dict

from ..contracts.canary_ir import CanaryReport


def export_canary_report(
    report: CanaryReport, out_dir: str, scene_id: str
) -> Dict[str, Any]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        asdict(report),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    sha = hashlib.sha256(payload).hexdigest()
    path = str(Path(out_dir) / f"{scene_id}:{sha[:12]}:luma_canary_report.json")
    with open(path, "wb") as f:
        f.write(payload)
    return {"path": path, "bytes_sha256": sha, "items": len(report.items)}
