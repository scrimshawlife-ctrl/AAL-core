# AAL-core Function Registry (DFD)

**ᛞᚠᛞ** - Dynamic Function Discovery

## Quick Start

```python
from aal_core.bus import EventBus
from aal_core.services.fn_registry import FunctionRegistry

# Initialize
bus = EventBus()
registry = FunctionRegistry(bus, overlays_root=".aal/overlays")

# Build catalog
registry.tick()

# Get snapshot
snapshot = registry.get_snapshot()
print(f"Catalog hash: {snapshot.catalog_hash}")
print(f"Function count: {snapshot.count}")

# Inspect functions
for fn in snapshot.descriptors:
    print(f"  - {fn['id']}: {fn['name']} ({fn['kind']})")
```

## Module Structure

```
fn_registry/
├── __init__.py           # Public API
├── service.py            # FunctionRegistry + CatalogSnapshot
├── validate.py           # Schema validation
└── sources/
    ├── manifest.py       # Load overlay manifests
    ├── py_entrypoints.py # Python module exports
    └── http.py           # HTTP service discovery
```

## Adding to Existing FastAPI App

```python
from fastapi import FastAPI
from aal_core.bus import EventBus
from aal_core.services.fn_registry import (
    FunctionRegistry,
    bind_fn_registry_routes
)

app = FastAPI()
bus = EventBus()
registry = FunctionRegistry(bus, overlays_root=".aal/overlays")

# Initial catalog build
registry.tick()

# Bind routes (adds GET /fn/catalog)
bind_fn_registry_routes(app, registry)
```

## Discovery Sources

### 1. Overlay Manifests

Location: `.aal/overlays/<name>/manifest.json`

```json
{
  "name": "abraxas",
  "version": "2.1",
  "py_exports": ["abraxas.exports"],
  "service_url": "http://localhost:8088"
}
```

### 2. Python Exports

Module: `abraxas.exports`

```python
EXPORTS = [
    {
        "id": "abx.metric.alive.v1",
        "name": "Alive Metric",
        "kind": "metric",
        # ... full FunctionDescriptor
    },
    # ... more functions
]
```

### 3. HTTP Endpoints (Optional)

Endpoint: `GET {service_url}/abx/functions`

Response:
```json
{
  "functions": [
    {
      "id": "remote.op.example.v1",
      # ... full FunctionDescriptor
    }
  ]
}
```

## Validation

```python
from aal_core.services.fn_registry import validate_descriptors

descriptors = [
    {
        "id": "test.metric.v1",
        "name": "Test",
        "kind": "metric",
        "version": "1.0.0",
        "owner": "test",
        "entrypoint": "test:fn",
        "inputs_schema": {},
        "outputs_schema": {},
        "capabilities": [],
        "provenance": {
            "repo": "...",
            "commit": "...",
            "artifact_hash": "...",
            "generated_at": 123
        }
    }
]

validate_descriptors(descriptors)  # Raises ValueError if invalid
```

## Bus Events

Subscribe to catalog updates:

```python
def on_catalog_update(topic, payload):
    print(f"Catalog updated: {payload['catalog_hash']}")
    print(f"Function count: {payload['count']}")

bus.subscribe("fn.registry.updated", on_catalog_update)
```

## Testing

```bash
# Run all tests
pytest tests/test_fn_registry.py -v

# Test specific component
pytest tests/test_fn_registry.py::test_validation -v

# Test with coverage
pytest tests/test_fn_registry.py --cov=aal_core.services.fn_registry
```

## Performance

- Initial catalog build: ~10-50ms (depends on overlay count)
- Catalog hash computation: ~1-5ms
- HTTP discovery timeout: 1.5s per service (configurable)
- Memory: ~1KB per function descriptor

## Design Decisions

### Why Explicit Exports?

Prevents unbounded reflection and maintains SEED entropy minimization principle.

### Why Merge by ID?

Enables override mechanism: later sources can override earlier ones.

### Why SHA256 Hash?

Provides strong collision resistance for state fingerprinting and drift detection.

### Why Silent HTTP Failures?

Registry must survive partial outages. HTTP sources are optional.

## See Also

- [Full DFD Specification](../../../docs/DFD_SPEC.md)
- [Function Descriptor Schema](../../../docs/DFD_SPEC.md#function-descriptor-schema)
- [API Endpoints](../../../docs/DFD_SPEC.md#api-endpoints)
