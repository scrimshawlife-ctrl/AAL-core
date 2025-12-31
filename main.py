#!/usr/bin/env python3
"""
AAL-Core: Append-only overlay bus with provenance logging
"""
import os
import json
import hashlib
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from bus import load_overlays, enforce_phase_policy

app = FastAPI(title="AAL-Core", version="1.0.0")

# Paths
OVERLAYS_DIR = Path(__file__).parent / ".aal" / "overlays"
LOGS_DIR = Path(__file__).parent / "logs"
PROVENANCE_LOG = LOGS_DIR / "provenance.jsonl"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)


class InvokeRequest(BaseModel):
    phase: str
    data: Dict[str, Any]


class InvokeResponse(BaseModel):
    ok: bool
    overlay: str
    phase: str
    request_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp_ms: int
    payload_hash: str


def get_overlay_info(overlay_name: str):
    """Load overlay manifest using bus registry."""
    overlays = load_overlays(OVERLAYS_DIR)

    if overlay_name not in overlays:
        raise HTTPException(404, f"Overlay '{overlay_name}' not found")

    return overlays[overlay_name]  # Returns (Path, OverlayManifest, hash)


def compute_payload_hash(data: Dict[str, Any]) -> str:
    """Compute deterministic SHA256 hash of payload."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    """Append event to JSONL log (atomic, append-only)."""
    with open(path, "a") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def invoke_overlay_subprocess(
    overlay_dir: Path,
    overlay_name: str,
    manifest,  # OverlayManifest
    phase: str,
    data: Dict[str, Any],
    request_id: str
) -> Dict[str, Any]:
    """Execute overlay via subprocess with timeout."""
    entrypoint = manifest.entrypoint
    timeout_ms = manifest.timeout_ms

    # Build overlay request
    overlay_request = {
        "overlay": overlay_name,
        "version": manifest.version,
        "phase": phase,
        "request_id": request_id,
        "timestamp_ms": int(time.time() * 1000),
        "payload": data
    }

    # Execute
    cmd = entrypoint.split()
    try:
        result = subprocess.run(
            cmd,
            input=json.dumps(overlay_request).encode("utf-8"),
            capture_output=True,
            timeout=timeout_ms / 1000.0,
            cwd=overlay_dir,
            check=False
        )

        # Parse output
        if result.returncode == 0:
            return json.loads(result.stdout.decode("utf-8"))
        else:
            # Non-zero exit
            try:
                error_data = json.loads(result.stdout.decode("utf-8"))
                return error_data
            except:
                return {
                    "ok": False,
                    "overlay": overlay_name,
                    "phase": phase,
                    "request_id": request_id,
                    "error": result.stderr.decode("utf-8") or "Overlay exited with non-zero status",
                    "exit_code": result.returncode
                }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "overlay": overlay_name,
            "phase": phase,
            "request_id": request_id,
            "error": f"Overlay timeout ({timeout_ms}ms)",
            "error_type": "TimeoutExpired"
        }
    except Exception as e:
        return {
            "ok": False,
            "overlay": overlay_name,
            "phase": phase,
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__
        }


@app.get("/")
def root():
    """Health check."""
    return {
        "service": "AAL-Core",
        "version": "1.0.0",
        "status": "ok"
    }


@app.get("/overlays")
def list_overlays():
    """List available overlays."""
    overlays_data = load_overlays(OVERLAYS_DIR)
    overlays = []

    for name, (_, manifest, _) in overlays_data.items():
        overlays.append({
            "name": manifest.name,
            "version": manifest.version,
            "status": manifest.status,
            "phases": manifest.phases,
            "capabilities": manifest.capabilities,
            "op_policy": manifest.op_policy
        })

    return {"overlays": overlays}


@app.post("/invoke/{overlay_name}")
def invoke_overlay(overlay_name: str, req: InvokeRequest):
    """Invoke overlay with phase and data."""
    # Generate request ID
    request_id = f"{overlay_name}-{int(time.time() * 1000)}"

    # Load overlay manifest using bus registry
    overlay_dir, manifest, mf_hash = get_overlay_info(overlay_name)

    # Validate phase
    if req.phase not in manifest.phases:
        raise HTTPException(
            400,
            f"Invalid phase '{req.phase}' for overlay '{overlay_name}'. Valid: {manifest.phases}"
        )

<<<<<<< HEAD
    # Track op and required capabilities for ASCEND enforcement
    op = None
    op_required_caps = []

    # NEW: ASCEND op-policy enforcement
    if req.phase == "ASCEND":
        # Enforce op allowlist from manifest (trusted)
        op = req.data.get("op")
        if not isinstance(op, str) or not op:
            raise HTTPException(status_code=400, detail="ASCEND requires payload.data.op (string)")

        if op not in manifest.op_policy:
            raise HTTPException(status_code=403, detail=f"ASCEND op not allowed by manifest: {op}")

        op_required_caps = manifest.op_policy.get(op, [])

        # Enforce: overlay must declare any capability required by the op
        missing = [c for c in op_required_caps if c not in manifest.capabilities]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"ASCEND op '{op}' requires undeclared capabilities: {missing}"
            )

    # Phase policy enforcement (belt & suspenders: overlay caps + op-required caps)
    decision = enforce_phase_policy(req.phase, manifest.capabilities + list(op_required_caps))
    if not decision.ok:
        raise HTTPException(status_code=403, detail=decision.reason)
=======
    # Enforce phase policy
    overlay_caps = manifest.get("capabilities", [])
    policy_decision = enforce_phase_policy(req.phase, overlay_caps)
    if not policy_decision.ok:
        raise HTTPException(403, policy_decision.reason)
>>>>>>> origin/claude/add-phase-policy-enforcement-zE1qq

    # Compute payload hash for provenance
    payload_hash = compute_payload_hash(req.data)

    # Dev mode: log full payload for exact replay
    dev_log_payload = os.environ.get("AAL_DEV_LOG_PAYLOAD", "0") == "1"

    # Execute overlay
    start_ms = int(time.time() * 1000)
    overlay_response = invoke_overlay_subprocess(
        overlay_dir,
        overlay_name,
        manifest,
        req.phase,
        req.data,
        request_id
    )
    end_ms = int(time.time() * 1000)

    # Log to provenance (append-only)
    provenance_event = {
        "request_id": request_id,
        "timestamp_ms": start_ms,
        "overlay": overlay_name,
        "version": manifest.version,
        "phase": req.phase,
        "payload_hash": payload_hash,
        "manifest_hash": mf_hash,
        "ok": overlay_response.get("ok"),
        "duration_ms": end_ms - start_ms,
        "error": overlay_response.get("error"),
        "op": op,
        "op_required_caps": op_required_caps
    }

    # Dev-only: store full payload for exact replay
    if dev_log_payload:
        provenance_event["payload"] = req.data

    append_jsonl(PROVENANCE_LOG, provenance_event)

    # Return response
    return {
        "ok": overlay_response.get("ok"),
        "overlay": overlay_name,
        "phase": req.phase,
        "request_id": request_id,
        "result": overlay_response.get("result"),
        "error": overlay_response.get("error"),
        "timestamp_ms": end_ms,
        "payload_hash": payload_hash
    }


@app.get("/provenance")
def get_provenance(limit: int = 100):
    """Retrieve recent provenance events."""
    if not PROVENANCE_LOG.exists():
        return {"events": []}

    with open(PROVENANCE_LOG) as f:
        lines = f.readlines()

    events = [json.loads(line) for line in lines[-limit:]]
    return {"events": events, "count": len(events)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
