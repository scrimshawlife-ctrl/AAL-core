from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import hashlib
import json
from typing import Any, Dict, List

from ..contracts.proposal_ir import PatternProposal


def export_proposals(
    proposals: List[PatternProposal], out_dir: str, scene_id: str
) -> Dict[str, Any]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    payload = [asdict(p) for p in proposals]
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    path = str(Path(out_dir) / f"{scene_id}:{sha[:12]}:luma_proposals.json")
    with open(path, "wb") as f:
        f.write(data)
    return {"path": path, "bytes_sha256": sha, "count": len(proposals)}
