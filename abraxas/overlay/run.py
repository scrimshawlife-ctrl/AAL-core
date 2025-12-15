#!/usr/bin/env python3
"""
Abraxas Overlay Runner
Accepts JSON on stdin, returns JSON on stdout.
"""
import sys
import json
import time
from typing import Dict, Any


def handle_open(payload: Dict[str, Any]) -> Dict[str, Any]:
    """OPEN phase: Initial request processing."""
    return {
        "status": "open_complete",
        "prompt_received": payload.get("prompt", ""),
        "intent": payload.get("intent", "unknown")
    }


def handle_align(payload: Dict[str, Any]) -> Dict[str, Any]:
    """ALIGN phase: Contextual alignment."""
    return {
        "status": "aligned",
        "context": "abraxas_kernel",
        "alignment_complete": True
    }


def handle_ascend(payload: Dict[str, Any]) -> Dict[str, Any]:
    """ASCEND phase: Exec-capable operations (requires 'exec' capability)."""
    import hashlib

    op = payload.get("op", "unknown")
    value = payload.get("value", "")

    if op == "hash":
        # Simulate an exec operation (computing hash)
        result = hashlib.sha256(value.encode()).hexdigest()
        return {
            "status": "ascended",
            "operation": "hash",
            "input": value,
            "output": result,
            "exec_performed": True
        }
    else:
        return {
            "status": "ascended",
            "operation": op,
            "message": f"Unknown operation: {op}",
            "exec_performed": False
        }


def handle_clear(payload: Dict[str, Any]) -> Dict[str, Any]:
    """CLEAR phase: Read-only operations."""
    return {
        "status": "cleared",
        "analysis": f"Analyzed: {payload.get('prompt', 'N/A')}",
        "readonly": True
    }


def handle_seal(payload: Dict[str, Any]) -> Dict[str, Any]:
    """SEAL phase: Finalization."""
    return {
        "status": "sealed",
        "finalized": True,
        "timestamp_ms": int(time.time() * 1000)
    }


PHASE_HANDLERS = {
    "OPEN": handle_open,
    "ALIGN": handle_align,
    "ASCEND": handle_ascend,
    "CLEAR": handle_clear,
    "SEAL": handle_seal,
}


def run_overlay(request: Dict[str, Any]) -> Dict[str, Any]:
    """Main overlay entry point."""
    overlay = request.get("overlay")
    version = request.get("version")
    phase = request.get("phase")
    request_id = request.get("request_id")
    payload = request.get("payload", {})

    # Validate (accept both abraxas and abraxas_exec variants)
    if not overlay or not overlay.startswith("abraxas"):
        return {
            "ok": False,
            "error": f"Unknown overlay: {overlay}",
            "request_id": request_id
        }

    if phase not in PHASE_HANDLERS:
        return {
            "ok": False,
            "error": f"Unknown phase: {phase}",
            "request_id": request_id,
            "valid_phases": list(PHASE_HANDLERS.keys())
        }

    # Execute phase handler
    try:
        result = PHASE_HANDLERS[phase](payload)
        return {
            "ok": True,
            "overlay": overlay,
            "version": version,
            "phase": phase,
            "request_id": request_id,
            "result": result,
            "timestamp_ms": int(time.time() * 1000)
        }
    except Exception as e:
        return {
            "ok": False,
            "overlay": overlay,
            "phase": phase,
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__
        }


def main():
    """Read JSON from stdin, execute, write JSON to stdout."""
    try:
        request = json.load(sys.stdin)
        response = run_overlay(request)
        print(json.dumps(response, indent=2))
        sys.exit(0 if response.get("ok") else 1)
    except json.JSONDecodeError as e:
        error_response = {
            "ok": False,
            "error": f"Invalid JSON input: {e}",
            "error_type": "JSONDecodeError"
        }
        print(json.dumps(error_response, indent=2))
        sys.exit(1)
    except Exception as e:
        error_response = {
            "ok": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        print(json.dumps(error_response, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
