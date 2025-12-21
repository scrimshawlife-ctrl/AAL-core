#!/usr/bin/env python3
"""
AAL-Core: Append-only overlay bus with provenance logging + Dynamic Function Discovery
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

# AAL-core services
from aal_core.bus import EventBus
from aal_core.services.fn_registry import FunctionRegistry, bind_fn_registry_routes


app = FastAPI(title="AAL-Core", version="1.0.0")

# Paths
OVERLAYS_DIR = Path(__file__).parent / ".aal" / "overlays"
LOGS_DIR = Path(__file__).parent / "logs"
PROVENANCE_LOG = LOGS_DIR / "provenance.jsonl"
EVENTS_LOG = LOGS_DIR / "events.jsonl"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Initialize event bus
event_bus = EventBus(log_path=EVENTS_LOG)

# Initialize function registry
fn_registry = FunctionRegistry(
    bus=event_bus,
    overlays_root=str(OVERLAYS_DIR)
)

# Build initial catalog
fn_registry.tick()


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


def load_overlay_manifest(overlay_name: str) -> Dict[str, Any]:
    """Load and parse overlay manifest.json"""
    manifest_path = OVERLAYS_DIR / overlay_name / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(404, f"Overlay '{overlay_name}' not found")

    with open(manifest_path) as f:
        return json.load(f)


def compute_payload_hash(data: Dict[str, Any]) -> str:
    """Compute deterministic SHA256 hash of payload."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, event: Dict[str, Any]) -> None:
    """Append event to JSONL log (atomic, append-only)."""
    with open(path, "a") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def invoke_overlay_subprocess(
    overlay_name: str,
    manifest: Dict[str, Any],
    phase: str,
    data: Dict[str, Any],
    request_id: str
) -> Dict[str, Any]:
    """Execute overlay via subprocess with timeout."""
    overlay_dir = OVERLAYS_DIR / overlay_name
    entrypoint = manifest.get("entrypoint", "python src/run.py")
    timeout_ms = manifest.get("timeout_ms", 5000)

    # Build overlay request
    overlay_request = {
        "overlay": overlay_name,
        "version": manifest.get("version"),
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
    overlays = []
    if OVERLAYS_DIR.exists():
        for overlay_dir in OVERLAYS_DIR.iterdir():
            if overlay_dir.is_dir():
                manifest_path = overlay_dir / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    overlays.append({
                        "name": overlay_dir.name,
                        "version": manifest.get("version"),
                        "status": manifest.get("status"),
                        "phases": manifest.get("phases", []),
                        "capabilities": manifest.get("capabilities", [])
                    })
    return {"overlays": overlays}


@app.post("/invoke/{overlay_name}")
def invoke_overlay(overlay_name: str, req: InvokeRequest):
    """Invoke overlay with phase and data."""
    # Generate request ID
    request_id = f"{overlay_name}-{int(time.time() * 1000)}"

    # Load manifest
    manifest = load_overlay_manifest(overlay_name)

    # Validate phase
    valid_phases = manifest.get("phases", [])
    if req.phase not in valid_phases:
        raise HTTPException(
            400,
            f"Invalid phase '{req.phase}' for overlay '{overlay_name}'. Valid: {valid_phases}"
        )

    # Compute payload hash for provenance
    payload_hash = compute_payload_hash(req.data)

    # Dev mode: log full payload for exact replay
    dev_log_payload = os.environ.get("AAL_DEV_LOG_PAYLOAD", "0") == "1"

    # Execute overlay
    start_ms = int(time.time() * 1000)
    overlay_response = invoke_overlay_subprocess(
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
        "version": manifest.get("version"),
        "phase": req.phase,
        "payload_hash": payload_hash,
        "ok": overlay_response.get("ok"),
        "duration_ms": end_ms - start_ms,
        "error": overlay_response.get("error")
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


@app.get("/events")
def get_events(limit: int = 100):
    """Retrieve recent bus events."""
    events = event_bus.get_recent_events(limit=limit)
    return {"events": events, "count": len(events)}


@app.post("/fn/rebuild")
def rebuild_fn_catalog():
    """
    Manually trigger function catalog rebuild.

    Returns updated catalog hash and count.
    """
    fn_registry.tick()
    snapshot = fn_registry.get_snapshot()

    return {
        "ok": True,
        "catalog_hash": snapshot.catalog_hash,
        "count": snapshot.count,
        "generated_at_unix": snapshot.generated_at_unix
    }


# Bind function registry routes
bind_fn_registry_routes(app, fn_registry)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
