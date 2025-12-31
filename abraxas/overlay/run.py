#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from typing import Any, Dict


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _ok(req: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "overlay": req.get("overlay"),
        "phase": req.get("phase"),
        "request_id": req.get("request_id"),
        "result": result,
        "error": None,
    }


def _err(req: Dict[str, Any], msg: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "overlay": req.get("overlay"),
        "phase": req.get("phase"),
        "request_id": req.get("request_id"),
        "result": None,
        "error": msg,
    }


def main() -> int:
    req = json.loads(sys.stdin.read() or "{}")
    phase = str(req.get("phase") or "OPEN")
    payload: Dict[str, Any] = dict(req.get("payload") or {})

    if phase == "ASCEND":
        op = str(payload.get("op") or "")
        if op == "hash":
            val = str(payload.get("value") or "")
            out = _ok(
                req,
                {
                    "status": "ascended",
                    "operation": "hash",
                    "exec_performed": True,
                    "output": _sha256_hex(val),
                },
            )
        elif op == "echo":
            out = _ok(
                req,
                {
                    "status": "ascended",
                    "operation": "echo",
                    "exec_performed": True,
                    "output": payload.get("value"),
                },
            )
        else:
            out = _err(req, f"unknown_op:{op}")
    elif phase == "CLEAR":
        out = _ok(req, {"readonly": True, "status": "cleared"})
    else:
        out = _ok(req, {"status": phase.lower(), "echo": payload})

    sys.stdout.write(json.dumps(out, sort_keys=True))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())

