#!/usr/bin/env python3
"""
Replay Tool: Re-execute a logged provenance event with exact payload
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import subprocess
import time
import hashlib

ROOT = Path(__file__).resolve().parents[1]
OVERLAYS_DIR = ROOT / ".aal" / "overlays"
LOG_PATH = ROOT / "logs" / "provenance.jsonl"


def compute_manifest_hash(manifest: dict) -> str:
    """Compute deterministic SHA256 hash of manifest."""
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_line(n: int) -> dict:
    """Read line N from provenance log (1-indexed)."""
    if not LOG_PATH.exists():
        raise SystemExit(f"Missing log: {LOG_PATH}")
    with LOG_PATH.open("r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    if n < 1 or n > len(lines):
        raise SystemExit(f"Line out of range: 1..{len(lines)}")
    return json.loads(lines[n - 1])


def load_overlay_manifest(overlay_name: str) -> tuple[dict, str]:
    """Load manifest and compute its hash."""
    manifest_path = OVERLAYS_DIR / overlay_name / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Overlay manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        manifest = json.load(f)

    manifest_hash = compute_manifest_hash(manifest)
    return manifest, manifest_hash


def replay_overlay(
    overlay_name: str,
    manifest: dict,
    phase: str,
    payload: dict,
    request_id: str
) -> dict:
    """Execute overlay via subprocess (same as main.py)."""
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
        "payload": payload
    }

    # Execute
    cmd = entrypoint.split()
    try:
        start_ms = int(time.time() * 1000)
        result = subprocess.run(
            cmd,
            input=json.dumps(overlay_request).encode("utf-8"),
            capture_output=True,
            timeout=timeout_ms / 1000.0,
            cwd=overlay_dir,
            check=False
        )
        end_ms = int(time.time() * 1000)

        # Parse output
        stdout = result.stdout.decode("utf-8")
        stderr = result.stderr.decode("utf-8")

        if result.returncode == 0:
            try:
                output_json = json.loads(stdout)
            except json.JSONDecodeError:
                output_json = None

            return {
                "ok": True,
                "overlay": overlay_name,
                "phase": phase,
                "exit_code": result.returncode,
                "duration_ms": end_ms - start_ms,
                "stdout": stdout,
                "stderr": stderr,
                "output_json": output_json
            }
        else:
            # Non-zero exit
            try:
                error_data = json.loads(stdout)
                output_json = error_data
            except:
                output_json = None

            return {
                "ok": False,
                "overlay": overlay_name,
                "phase": phase,
                "exit_code": result.returncode,
                "duration_ms": end_ms - start_ms,
                "stdout": stdout,
                "stderr": stderr,
                "output_json": output_json,
                "error": stderr or "Overlay exited with non-zero status"
            }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "overlay": overlay_name,
            "phase": phase,
            "exit_code": -1,
            "duration_ms": timeout_ms,
            "error": f"Overlay timeout ({timeout_ms}ms)",
            "error_type": "TimeoutExpired"
        }
    except Exception as e:
        return {
            "ok": False,
            "overlay": overlay_name,
            "phase": phase,
            "exit_code": -1,
            "duration_ms": 0,
            "error": str(e),
            "error_type": type(e).__name__
        }


def main() -> int:
    """Main replay entry point."""
    if len(sys.argv) != 2:
        print("Usage: python3 TOOLS/replay.py <line_number>")
        print("\nReplay a provenance event by line number (1-indexed).")
        print("Note: Requires AAL_DEV_LOG_PAYLOAD=1 to have been set during original invocation.")
        return 2

    try:
        line_no = int(sys.argv[1])
    except ValueError:
        print(f"Error: Line number must be an integer, got: {sys.argv[1]}")
        return 2

    # Read provenance event
    event = read_line(line_no)

    overlay = event.get("overlay")
    phase = event.get("phase")

    # Exact replay requires payload to be logged (dev mode)
    payload = event.get("payload")
    if payload is None:
        raise SystemExit(
            "❌ This provenance line does not include 'payload'.\n\n"
            "Enable dev payload logging with:\n"
            "  export AAL_DEV_LOG_PAYLOAD=1\n\n"
            "Then invoke the overlay again to capture replayable runs."
        )
    if not isinstance(payload, dict):
        raise SystemExit("Invalid payload in log (expected dict)")

    # Load current manifest
    manifest, manifest_hash = load_overlay_manifest(overlay)

    # Optionally validate manifest hasn't drifted
    expected_hash = event.get("manifest_hash")
    if expected_hash and manifest_hash != expected_hash:
        print(
            f"⚠️  Warning: Manifest hash mismatch.\n"
            f"  Original: {expected_hash}\n"
            f"  Current:  {manifest_hash}\n"
            f"\nProceeding with replay using current manifest...\n",
            file=sys.stderr
        )

    # Generate replay request ID
    request_id = f"replay-{line_no}-{int(time.time() * 1000)}"

    print(f"Replaying event from line {line_no}:")
    print(f"  Overlay: {overlay}")
    print(f"  Phase: {phase}")
    print(f"  Request ID: {event.get('request_id')}")
    print(f"  Payload Hash: {event.get('payload_hash')}\n")

    # Execute replay
    result = replay_overlay(
        overlay_name=overlay,
        manifest=manifest,
        phase=phase,
        payload=payload,
        request_id=request_id
    )

    # Output result
    print("Replay Result:")
    print(json.dumps(result, sort_keys=True, indent=2))

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
