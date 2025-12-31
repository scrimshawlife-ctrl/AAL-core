"""
Abraxas Function Exports
=========================
Explicit function descriptor exports for Dynamic Function Discovery (DFD).

Every Abraxas metric/rune/op must be declared here for discoverability.
"""

import time

# Provenance metadata
REPO = "https://github.com/scrimshawlife-ctrl/AAL-core"
COMMIT = "62f3a6e825cdc7f766dc9ac31342ed57f1750039"
ARTIFACT_HASH = "sha256:abraxas-2.1"  # Version-based artifact hash
GENERATED_AT = int(time.time())


# --------------------------------------------------
# Abraxas Core Metrics
# --------------------------------------------------

METRIC_ALIVE = {
    "id": "abx.metric.alive.v1",
    "name": "Alive Metric",
    "kind": "metric",
    "rune": "ᚨ",  # Ansuz - communication, life force
    "version": "1.0.0",
    "owner": "abraxas",
    "entrypoint": "abraxas.metrics.alive:check_alive",
    "inputs_schema": {
        "type": "object",
        "properties": {},
        "required": []
    },
    "outputs_schema": {
        "type": "object",
        "properties": {
            "alive": {"type": "boolean"},
            "timestamp": {"type": "integer"}
        },
        "required": ["alive", "timestamp"]
    },
    "capabilities": ["no_net", "read_only"],
    "cost_hint": {
        "p50_ms": 1,
        "p95_ms": 5
    },
    "provenance": {
        "repo": REPO,
        "commit": COMMIT,
        "artifact_hash": ARTIFACT_HASH,
        "generated_at": GENERATED_AT
    }
}

METRIC_ENTROPY = {
    "id": "abx.metric.entropy.v1",
    "name": "Entropy Metric",
    "kind": "metric",
    "rune": "ᛖ",  # Ehwaz - movement, entropy
    "version": "1.0.0",
    "owner": "abraxas",
    "entrypoint": "abraxas.metrics.entropy:measure_entropy",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "data": {"type": "string", "description": "Data to measure entropy of"}
        },
        "required": ["data"]
    },
    "outputs_schema": {
        "type": "object",
        "properties": {
            "entropy": {"type": "number"},
            "bits": {"type": "number"}
        },
        "required": ["entropy", "bits"]
    },
    "capabilities": ["no_net", "read_only"],
    "cost_hint": {
        "p50_ms": 10,
        "p95_ms": 50
    },
    "provenance": {
        "repo": REPO,
        "commit": COMMIT,
        "artifact_hash": ARTIFACT_HASH,
        "generated_at": GENERATED_AT
    }
}


# --------------------------------------------------
# Abraxas Runes (Symbolic Operations)
# --------------------------------------------------

RUNE_OPEN = {
    "id": "abx.rune.open.v1",
    "name": "OPEN Phase Rune",
    "kind": "rune",
    "rune": "ᚩ",  # Os - opening, mouth, signal
    "version": "1.0.0",
    "owner": "abraxas",
    "entrypoint": "abraxas.overlay.run:handle_open",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "phase": {"type": "string", "enum": ["OPEN"]},
            "payload": {"type": "object"}
        },
        "required": ["phase", "payload"]
    },
    "outputs_schema": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "result": {"type": "object"}
        },
        "required": ["ok"]
    },
    "capabilities": ["analysis"],
    "cost_hint": {
        "p50_ms": 100,
        "p95_ms": 500
    },
    "provenance": {
        "repo": REPO,
        "commit": COMMIT,
        "artifact_hash": ARTIFACT_HASH,
        "generated_at": GENERATED_AT
    }
}

RUNE_SEAL = {
    "id": "abx.rune.seal.v1",
    "name": "SEAL Phase Rune",
    "kind": "rune",
    "rune": "ᛋ",  # Sowilo - sun, seal, completion
    "version": "1.0.0",
    "owner": "abraxas",
    "entrypoint": "abraxas.overlay.run:handle_seal",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "phase": {"type": "string", "enum": ["SEAL"]},
            "payload": {"type": "object"}
        },
        "required": ["phase", "payload"]
    },
    "outputs_schema": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "result": {"type": "object"}
        },
        "required": ["ok"]
    },
    "capabilities": ["analysis"],
    "cost_hint": {
        "p50_ms": 150,
        "p95_ms": 600
    },
    "provenance": {
        "repo": REPO,
        "commit": COMMIT,
        "artifact_hash": ARTIFACT_HASH,
        "generated_at": GENERATED_AT
    }
}


# --------------------------------------------------
# Abraxas Ops (Composite Operations)
# --------------------------------------------------

OP_FULL_CYCLE = {
    "id": "abx.op.full_cycle.v1",
    "name": "Full Abraxas Cycle",
    "kind": "op",
    "rune": "ᛞᚠᛞ",  # DFD - Full cycle through all phases
    "version": "1.0.0",
    "owner": "abraxas",
    "entrypoint": "abraxas.ops.cycle:run_full_cycle",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "payload": {"type": "object"}
        },
        "required": ["payload"]
    },
    "outputs_schema": {
        "type": "object",
        "properties": {
            "phases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "phase": {"type": "string"},
                        "ok": {"type": "boolean"},
                        "result": {"type": "object"}
                    }
                }
            },
            "complete": {"type": "boolean"}
        },
        "required": ["phases", "complete"]
    },
    "capabilities": ["analysis"],
    "cost_hint": {
        "p50_ms": 500,
        "p95_ms": 2000
    },
    "provenance": {
        "repo": REPO,
        "commit": COMMIT,
        "artifact_hash": ARTIFACT_HASH,
        "generated_at": GENERATED_AT
    }
}


# --------------------------------------------------
# EXPORTS List (Required by DFD)
# --------------------------------------------------

EXPORTS = [
    # Metrics
    METRIC_ALIVE,
    METRIC_ENTROPY,

    # Runes
    RUNE_OPEN,
    RUNE_SEAL,

    # Ops
    OP_FULL_CYCLE,
]
