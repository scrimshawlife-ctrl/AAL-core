import sys, json, hashlib

def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

raw = sys.stdin.read()
req = json.loads(raw)

# Minimal deterministic echo: this is *not* Abraxas itself,
# it's a harness proving execution & provenance flow.
payload = req.get("payload", {})
phase = req.get("phase", "OPEN")

out = {
    "overlay": req.get("overlay"),
    "phase": phase,
    "request_id": req.get("request_id"),
    "payload_hash": sha(json.dumps(payload, sort_keys=True)),
    "note": "Overlay execution harness OK (replace with real Abraxas adapter later)"
}

sys.stdout.write(json.dumps(out, sort_keys=True))
