from __future__ import annotations
from pathlib import Path
import os
import shlex
import subprocess
import time
import json
from typing import Any, Dict, Optional

from .types import OverlayManifest, Phase, InvocationResult
from .provenance import hash_event

def _clean_env() -> dict[str, str]:
    # Minimal environment — deterministic-ish, avoids inheriting noisy vars.
    keep = ["PATH", "PYTHONPATH"]
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["PYTHONUNBUFFERED"] = "1"
    env["AAL_SANDBOX"] = "1"
    return env

def run_overlay(
    overlay_dir: Path,
    manifest: OverlayManifest,
    phase: Phase,
    payload: Dict[str, Any],
    request_id: str,
    timestamp_ms: int,
) -> InvocationResult:
    start = time.time()
    cmd = shlex.split(manifest.entrypoint)

    # Provide input via stdin as canonical JSON
    stdin_obj = {
        "overlay": manifest.name,
        "version": manifest.version,
        "phase": phase,
        "request_id": request_id,
        "timestamp_ms": timestamp_ms,
        "payload": payload,
    }
    stdin_str = json.dumps(stdin_obj, sort_keys=True)

    # Provenance hash includes what we *intend* to execute + inputs
    prov_event = {
        "overlay": manifest.name,
        "version": manifest.version,
        "phase": phase,
        "entrypoint": manifest.entrypoint,
        "request_id": request_id,
        "timestamp_ms": timestamp_ms,
        "payload": payload,
    }
    prov_hash = hash_event(prov_event)

    try:
        p = subprocess.run(
            cmd,
            input=stdin_str.encode("utf-8"),
            cwd=str(overlay_dir),
            env=_clean_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(0.1, manifest.timeout_ms / 1000.0),
            check=False,
        )
        duration_ms = int((time.time() - start) * 1000)
        stdout = p.stdout.decode("utf-8", errors="replace")
        stderr = p.stderr.decode("utf-8", errors="replace")

        # Optional: if stdout is JSON, parse it
        out_json: Optional[Dict[str, Any]] = None
        s = stdout.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                out_json = json.loads(s)
            except Exception:
                out_json = None

        return InvocationResult(
            ok=(p.returncode == 0),
            overlay=manifest.name,
            phase=phase,
            stdout=stdout,
            stderr=stderr,
            exit_code=p.returncode,
            duration_ms=duration_ms,
            provenance_hash=prov_hash,
            output_json=out_json,
        )

    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.time() - start) * 1000)
        return InvocationResult(
            ok=False,
            overlay=manifest.name,
            phase=phase,
            stdout=(e.stdout.decode("utf-8", errors="replace") if e.stdout else ""),
            stderr="TIMEOUT",
            exit_code=124,
            duration_ms=duration_ms,
            provenance_hash=prov_hash,
            output_json=None,
        )
