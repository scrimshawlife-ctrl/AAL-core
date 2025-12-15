from __future__ import annotations
from pathlib import Path
import json
import hashlib
import time
from typing import Any, Dict

def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def hash_event(event: Dict[str, Any]) -> str:
    raw = canonical_json(event).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def append_jsonl(log_path: Path, event: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(canonical_json(event) + "\n")

def now_unix_ms() -> int:
    return int(time.time() * 1000)
