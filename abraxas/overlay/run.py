import hashlib
import json
import sys


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


raw = sys.stdin.read()
req = json.loads(raw or "{}")

payload = req.get("payload") or {}
phase = req.get("phase") or "OPEN"

if phase == "ASCEND":
    op = payload.get("op") or ""
    if op == "hash":
        value = str(payload.get("value", ""))
        out = {
            "ok": True,
            "result": {
                "status": "ascended",
                "operation": "hash",
                "exec_performed": True,
                "output": _sha256_hex(value),
            },
        }
    else:
        out = {
            "ok": False,
            "error": f"unknown_op:{op}",
            "result": {"status": "ascended", "operation": op, "exec_performed": False},
        }
elif phase == "CLEAR":
    out = {"ok": True, "result": {"readonly": True}}
else:
    out = {"ok": True, "result": {"readonly": False}}

sys.stdout.write(json.dumps(out, sort_keys=True))
