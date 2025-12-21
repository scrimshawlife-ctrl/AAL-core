# AAL-core Dynamic Function Discovery (DFD) Specification

**DFD Rune**: ᛞᚠᛞ
**Meaning**: Discovery → Catalog → Propagation

## Overview

The Dynamic Function Discovery (DFD) system enables AAL-core to automatically discover and index capabilities from Abraxas and overlay modules. This creates a canonical function catalog that updates automatically as the system grows, supporting modular hot-swappable overlays and eurorack-style interoperability.

## Core Principles (SEED + ABX-Core)

### 1. Deterministic Discovery
- Catalog must be reproducible from the same artifacts/manifests
- Discovery order is stable and well-defined
- Merge strategy is explicit (by function ID, sorted alphabetically)

### 2. Provenance Embedded
- Every function entry includes:
  - Repository URL
  - Commit hash
  - Artifact hash
  - Generation timestamp
- Full traceability from catalog entry to source

### 3. Entropy Minimization
- Bounded scanning only - no "import everything" reflection
- Explicit exports via `EXPORTS` list in modules
- No automatic discovery of arbitrary Python code

### 4. No Hidden Coupling
- Overlays and Abraxas communicate via stable schema
- Function descriptors follow canonical JSON shape
- Bus events for state propagation

### 5. Capability Sandbox
- Functions declare capabilities (e.g., `no_net`, `read_only`, `gpu_ok`)
- Cost hints provided (p50/p95 latency, token counts)
- Enables intelligent routing and resource management

## Architecture

### Discovery Sources (Priority Order)

1. **Overlay Manifests** (`.aal/overlays/<name>/manifest.json`)
   - Primary source of truth for overlay metadata
   - Contains `py_exports` list pointing to Python modules

2. **Python Exports** (`abraxas.exports`, etc.)
   - Modules must define `EXPORTS: List[Dict]`
   - Each dict is a complete FunctionDescriptor
   - Explicit enumeration - no reflection

3. **HTTP Runtime Handshake** (Optional)
   - `GET {service_url}/abx/functions`
   - For overlays running as remote services
   - Graceful degradation on network failure

### Merge Strategy

```python
# Discovery order is stable
py_descriptors = load_py_exports(manifests)
http_descriptors = fetch_remote_functions(manifests)

# Merge by ID (later sources override earlier)
merged = {}
for desc in py_descriptors + http_descriptors:
    merged[desc["id"]] = desc

# Sort by ID for determinism
descriptors = [merged[k] for k in sorted(merged.keys())]
```

### Catalog Hash

The catalog hash is a **state fingerprint** used for:
- Drift detection
- Update propagation
- Cache invalidation

Computation:
```python
canonical_json = json.dumps(
    descriptors,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False
)
hash = sha256(canonical_json).hexdigest()
catalog_hash = f"sha256:{hash}"
```

### Bus Events

When catalog hash changes:
```json
{
  "topic": "fn.registry.updated",
  "payload": {
    "catalog_hash": "sha256:abc123...",
    "generated_at_unix": 1703001234,
    "count": 42
  },
  "timestamp": "2025-12-21T12:34:56Z"
}
```

## Function Descriptor Schema

### Canonical JSON Shape

```json
{
  "id": "abx.metric.alive.v1",
  "name": "Alive Metric",
  "kind": "metric",
  "rune": "ᚨ",
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
    "repo": "https://github.com/scrimshawlife-ctrl/AAL-core",
    "commit": "62f3a6e825cdc7f766dc9ac31342ed57f1750039",
    "artifact_hash": "sha256:abraxas-2.1",
    "generated_at": 1703001234
  }
}
```

### Required Fields

- `id` (string): Stable identifier (e.g., `abx.metric.alive.v1`)
- `name` (string): Human-readable name
- `kind` (enum): `metric` | `rune` | `op` | `overlay_op` | `io`
- `version` (string): Semantic version
- `owner` (string): Abraxas or overlay name
- `entrypoint` (string): Python module:function OR HTTP endpoint
- `inputs_schema` (object): JSONSchema for inputs
- `outputs_schema` (object): JSONSchema for outputs
- `capabilities` (array): List of capability strings
- `provenance` (object): Source metadata

### Optional Fields

- `rune` (string): Symbolic binding (runic glyph)
- `cost_hint` (object): Performance hints

### Valid Kinds

- `metric`: Measurement/observation function
- `rune`: Symbolic operation (phase handler)
- `op`: Composite operation
- `overlay_op`: Overlay-specific operation
- `io`: Input/output function

### Capability Strings

Standard capabilities:
- `no_net`: Requires no network access
- `read_only`: Does not mutate state
- `gpu_ok`: Can utilize GPU
- `cpu_bound`: CPU-intensive
- `io_bound`: I/O-intensive
- `stateful`: Maintains internal state

## API Endpoints

### GET /fn/catalog

Get the complete function catalog.

**Response:**
```json
{
  "catalog_hash": "sha256:abc123...",
  "generated_at_unix": 1703001234,
  "count": 42,
  "functions": [<FunctionDescriptor>, ...]
}
```

### POST /fn/rebuild

Manually trigger catalog rebuild.

**Response:**
```json
{
  "ok": true,
  "catalog_hash": "sha256:def456...",
  "count": 43,
  "generated_at_unix": 1703001235
}
```

### GET /events?limit=100

Get recent bus events (including `fn.registry.updated`).

**Response:**
```json
{
  "events": [
    {
      "topic": "fn.registry.updated",
      "payload": {...},
      "timestamp": "2025-12-21T12:34:56Z"
    }
  ],
  "count": 15
}
```

## Implementation Guide

### Adding a New Function

1. **Define the FunctionDescriptor** in your exports module:

```python
# abraxas/exports.py

MY_FUNCTION = {
    "id": "abx.metric.my_metric.v1",
    "name": "My Metric",
    "kind": "metric",
    "rune": "ᛗ",
    "version": "1.0.0",
    "owner": "abraxas",
    "entrypoint": "abraxas.metrics.my_metric:compute",
    "inputs_schema": {
        "type": "object",
        "properties": {
            "value": {"type": "number"}
        },
        "required": ["value"]
    },
    "outputs_schema": {
        "type": "object",
        "properties": {
            "result": {"type": "number"}
        },
        "required": ["result"]
    },
    "capabilities": ["read_only", "no_net"],
    "cost_hint": {
        "p50_ms": 5,
        "p95_ms": 15
    },
    "provenance": {
        "repo": REPO,
        "commit": COMMIT,
        "artifact_hash": ARTIFACT_HASH,
        "generated_at": GENERATED_AT
    }
}

EXPORTS = [
    # ... other exports
    MY_FUNCTION,
]
```

2. **The catalog updates automatically** on next `tick()` or when service starts

3. **Verify via API**:
```bash
curl http://localhost:8000/fn/catalog | jq '.functions[] | select(.id == "abx.metric.my_metric.v1")'
```

### Creating a New Overlay

1. **Create overlay directory**:
```bash
mkdir -p .aal/overlays/my_overlay
```

2. **Create manifest.json**:
```json
{
  "name": "my_overlay",
  "version": "1.0.0",
  "status": "active",
  "py_exports": ["my_overlay.exports"]
}
```

3. **Create exports module** (`my_overlay/exports.py`):
```python
EXPORTS = [
    {
        "id": "my_overlay.op.example.v1",
        "name": "Example Operation",
        "kind": "overlay_op",
        # ... full descriptor
    }
]
```

4. **Install overlay package** so it's importable
5. **Restart AAL-core** or call `POST /fn/rebuild`

## Testing

See `tests/test_fn_registry.py` for comprehensive test suite.

Run tests:
```bash
pytest tests/test_fn_registry.py -v
```

## Future Enhancements

- **Filesystem watch**: Auto-rebuild on manifest changes
- **Version resolution**: Handle multiple versions of same function
- **Dependency graph**: Track function dependencies
- **Remote caching**: Distributed catalog synchronization
- **Schema validation**: Stricter JSONSchema enforcement
- **Cost-based routing**: Use cost_hint for intelligent dispatch

## References

- [SEED Principles](../CANON.md)
- [ABX-Runes Catalog](../abx_runes/README.md)
- [Overlay Architecture](./OVERLAYS.md)
