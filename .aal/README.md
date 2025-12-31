# AAL Overlay System

**Modular Service Integration for AAL Core**

## Overview

The `.aal/` directory contains overlay manifests that integrate external services with AAL Core's resonant runtime. Overlays are modular, declarative service definitions that can be dynamically loaded and routed.

## Architecture

```
.aal/
├── README.md                    # This file
└── overlays/
    ├── psyfi/
    │   └── manifest.json        # Psy-Fi service overlay
    ├── beatoven/
    │   └── manifest.json        # BeatOven service overlay (future)
    └── [other_services]/
        └── manifest.json
```

## Overlay Manifest Structure

Each overlay defines:

```json
{
  "name": "service_name",
  "version": "semver",
  "description": "Human-readable description",

  "entrypoints": {
    "http": { "base_url": "http://..." },
    "grpc": { "host": "...", "port": ... },
    "local": { "module": "..." }
  },

  "capabilities": {
    "service.capability_name": {
      "runner": "http|grpc|local",
      "path": "/endpoint",
      "method": "POST|GET|...",
      "timeout_s": 30,
      "default_profile": "BALANCED|FAST|QUALITY",
      "degradation": {
        "max_fraction": 0.5,
        "disable_nonessential": true
      }
    }
  },

  "resources": {
    "prefers_gpu": false,
    "memory_mb": 1024,
    "notes": "Additional resource information"
  },

  "policy": {
    "deterministic": true,
    "cacheable": false,
    "requires_auth": false
  }
}
```

## Current Overlays

### Psy-Fi (`psyfi/`)
Psychological profiling and therapeutic intervention service.

**Capabilities:**
- `psyfi.ping` - Health check / basic echo
- `psyfi.echo` - Full echo with profile processing

**Entrypoint:** `http://127.0.0.1:8787`

**Status:** Initial overlay using stdlib HTTP server

## Integration with AAL Core

Overlays integrate with:

1. **AAL Hub** (`aal_core/hub.py`) - Service discovery and routing
2. **Capability Graph** (`alignment_core/capability_graph/`) - Capability registration
3. **Memory Governance** (`abx_runes/`) - Resource management
4. **Alignment System** (`aal_core/alignment/`) - Permission enforcement

## Adding a New Overlay

1. Create directory: `.aal/overlays/your_service/`
2. Add `manifest.json` following the schema above
3. Define capabilities with entrypoints
4. Register with AAL Hub (automatic discovery)
5. Test integration

Example:
```bash
mkdir -p .aal/overlays/my_service
# Create manifest.json
# Restart AAL Hub to discover new overlay
```

## Capability Naming Convention

Capabilities use dotted notation:
- `service.action` - Basic pattern
- `service.subsystem.action` - Nested services

Examples:
- `psyfi.ping` - Psy-Fi health check
- `psyfi.profile.analyze` - Psy-Fi profile analysis
- `beatoven.generate.melody` - BeatOven melody generation

## Resource Profiles

Overlays can specify resource preferences:

**FAST:** Low latency, minimal processing
- `timeout_s`: 5-10
- `degradation.max_fraction`: 0.25

**BALANCED:** Standard quality/latency tradeoff
- `timeout_s`: 10-30
- `degradation.max_fraction`: 0.5

**QUALITY:** Maximum quality, higher latency acceptable
- `timeout_s`: 30-120
- `degradation.max_fraction`: 0.75

## Degradation Strategies

When memory pressure increases (via ABX-Runes memory governance):

- `max_fraction`: Maximum memory fraction this service can use
- `disable_nonessential`: Turn off non-critical features
- `reduce_batch_size`: Process smaller batches
- `offload_to_disk`: Use disk cache instead of memory

## Policy Flags

### `deterministic`
- `true`: Same input → same output (cacheable, reproducible)
- `false`: Non-deterministic (e.g., sampling, randomness)

### `cacheable`
- `true`: Responses can be cached
- `false`: Fresh computation required

### `requires_auth`
- `true`: Capability requires authentication
- `false`: Public capability

## Security Considerations

Overlays run with:
- **Sandboxed execution** - Isolated from AAL Core internals
- **Rate limiting** - Per capability, per overlay
- **Capability-based permissions** - Only declared capabilities accessible
- **Alignment enforcement** - All overlays subject to AAC governance

## Monitoring

Each overlay should expose:
- Health check endpoint (`/health` or `ping` capability)
- Metrics endpoint (optional: `/metrics`)
- Resource usage reporting

## Future Enhancements

Planned overlay system features:
- **Hot reload** - Update overlays without restart
- **Versioning** - Multiple versions of same overlay
- **Failover** - Automatic fallback to backup instances
- **Load balancing** - Distribute across multiple instances
- **Service mesh** - Advanced routing and observability

## Example: Calling an Overlay

```python
from aal_core.overlay_dispatcher import call_capability

# Simple capability call
result = await call_capability(
    "psyfi.echo",
    payload={"text": "Hello Psy-Fi"}
)

# With resource profile
result = await call_capability(
    "psyfi.profile.analyze",
    payload={...},
    profile="QUALITY",
    timeout_override=60
)
```

## Governance

Overlay additions/modifications follow standard governance:
- Security review for new overlays
- Capability graph update
- Alignment policy verification
- Documentation requirements

---

**Overlays make AAL Core extensible. New services integrate via manifests, not code changes.**
