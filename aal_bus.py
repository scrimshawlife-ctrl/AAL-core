from fastapi import FastAPI, HTTPException
from pathlib import Path
import json
import time
import hashlib

APP_START = time.time()

ROOT = Path(__file__).resolve().parent
OVERLAYS_DIR = ROOT / ".aal" / "overlays"

app = FastAPI(title="AAL-Core Bus", version="0.1.0")


def hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_overlays():
    overlays = {}
    if not OVERLAYS_DIR.exists():
        return overlays

    for overlay in OVERLAYS_DIR.iterdir():
        manifest = overlay / "manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text())
            overlays[data["name"]] = {
                "path": overlay,
                "manifest": data
            }
    return overlays


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_sec": round(time.time() - APP_START, 2)
    }


@app.get("/overlays")
def list_overlays():
    overlays = load_overlays()
    return {
        "count": len(overlays),
        "overlays": list(overlays.keys())
    }


@app.post("/invoke/{overlay_name}")
def invoke_overlay(overlay_name: str, payload: dict):
    overlays = load_overlays()

    if overlay_name not in overlays:
        raise HTTPException(status_code=404, detail="Overlay not found")

    manifest = overlays[overlay_name]["manifest"]

    # Deterministic provenance
    invocation = {
        "overlay": overlay_name,
        "payload": payload,
        "timestamp": int(time.time()),
        "manifest_version": manifest.get("version", "unknown")
    }

    invocation["provenance_hash"] = hash_payload(invocation)

    # NOTE: No execution yet — this is intentional
    return {
        "status": "invoked",
        "overlay": overlay_name,
        "provenance_hash": invocation["provenance_hash"],
        "note": "Execution stub only (Canon-compliant)"
    }
