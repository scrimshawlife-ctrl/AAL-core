from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pathlib import Path
import uuid

from bus.overlay_registry import load_overlays
from bus.provenance import append_jsonl, now_unix_ms
from bus.sandbox import run_overlay
from bus.types import Phase

APP_START_MS = now_unix_ms()

ROOT = Path(__file__).resolve().parent
OVERLAYS_DIR = ROOT / ".aal" / "overlays"
LOG_PATH = ROOT / "logs" / "provenance.jsonl"

app = FastAPI(title="AAL-Core Bus", version="0.2.0")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_ms": now_unix_ms() - APP_START_MS,
        "overlays_dir": str(OVERLAYS_DIR),
    }


@app.get("/overlays")
def list_overlays():
    overlays = load_overlays(OVERLAYS_DIR)
    return {
        "count": len(overlays),
        "overlays": [
            {
                "name": mf.name,
                "version": mf.version,
                "status": mf.status,
                "phases": mf.phases,
                "timeout_ms": mf.timeout_ms,
            }
            for (_, mf) in overlays.values()
        ],
    }


@app.post("/invoke/{overlay_name}")
def invoke_overlay(overlay_name: str, payload: dict):
    """
    payload must include:
      - phase: one of OPEN/ALIGN/ASCEND/CLEAR/SEAL
      - data: dict (user payload)
    """
    overlays = load_overlays(OVERLAYS_DIR)
    if overlay_name not in overlays:
        raise HTTPException(status_code=404, detail="Overlay not found")

    overlay_dir, mf = overlays[overlay_name]

    phase = payload.get("phase")
    if phase not in ("OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"):
        raise HTTPException(status_code=400, detail="Invalid or missing phase")

    if phase not in mf.phases:
        raise HTTPException(
            status_code=400,
            detail=f"Overlay does not support phase {phase}",
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Missing payload.data dict")

    request_id = str(uuid.uuid4())
    ts = now_unix_ms()

    # Execute sandboxed
    result = run_overlay(
        overlay_dir=overlay_dir,
        manifest=mf,
        phase=phase,  # type: ignore
        payload=data,
        request_id=request_id,
        timestamp_ms=ts,
    )

    # Append provenance log (append-only)
    append_jsonl(
        LOG_PATH,
        {
            "request_id": request_id,
            "timestamp_ms": ts,
            "overlay": overlay_name,
            "phase": phase,
            "manifest_version": mf.version,
            "entrypoint": mf.entrypoint,
            "ok": result.ok,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
            "provenance_hash": result.provenance_hash,
        },
    )

    return {
        "request_id": request_id,
        "ok": result.ok,
        "overlay": result.overlay,
        "phase": result.phase,
        "duration_ms": result.duration_ms,
        "exit_code": result.exit_code,
        "provenance_hash": result.provenance_hash,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output_json": result.output_json,
    }
