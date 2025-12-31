# AAL-core

AAL-Core engine for Tachyon deployment with ABX-Runes Memory Governance Layer.

## Overview

AAL-Core provides a deterministic, modular memory governance system for ABX-Runes. This layer enables:

- **Runic memory contracts** - Declarative memory limits and behavior specifications
- **Live RAM stress monitoring** - Real-time memory pressure detection (0-1 scalar)
- **Automatic degradation** - Graceful fallback when RAM becomes scarce
- **KV cache management** - Policy-driven cache sizing and eviction
- **Multi-tier memory** - Support for LOCAL (DRAM), EXTENDED (CXL), and COLD (disk) tiers

## Architecture

```
abx_runes/
├── memory_runes.py          # Rune schema + parser
├── ram_stress.py            # Live RAM stress signal
└── scheduler_memory_layer.py # Enforcement hooks

tests/
└── test_memory_runes.py     # Basic hardening tests

examples/
└── memory_governance_example.py # Usage demonstration
```

## Quick Start

### 1. Define a Memory Profile

```python
from abx_runes.memory_runes import parse_memory_profile

RUNE_TEXT = """
MEM[SOFT=2048,HARD=4096,VOL=MED];
KV[CAP=0.2,POLICY=WINDOW,PURGE=ON_STRESS];
TIER=EXTENDED;
PRIORITY=7;
DEGRADE{
  STEP1:SHRINK_KV(0.75),
  STEP2:CONTEXT(4096),
  STEP3:DISABLE(HIGH_COST_METRICS),
  STEP4:BATCH(ASYNC),
  STEP5:OFFLOAD(EXTENDED)
}
"""

profile = parse_memory_profile(RUNE_TEXT)
```

### 2. Wrap Your Scheduler

```python
from abx_runes.scheduler_memory_layer import JobContext, MemoryAwareScheduler

def run_job(job: JobContext):
    # Your existing job execution logic
    # Read job.metadata for degradation parameters:
    # - kv_shrink_factor
    # - max_context_tokens
    # - disabled_features
    # - batch_mode
    # - offload_tier
    ...

mem_scheduler = MemoryAwareScheduler(run_job)
```

### 3. Submit Jobs

```python
job = JobContext(
    job_id="oracle-001",
    profile=profile,
    metadata={}
)

result = mem_scheduler.submit(job)
```

## Rune Syntax

### Memory Rune (Required)
```
MEM[SOFT=<mb>,HARD=<mb>,VOL=<LOW|MED|HIGH>]
```
- `SOFT`: Soft cap in MB (target)
- `HARD`: Hard cap in MB (absolute limit)
- `VOL`: Volatility tier (memory churn rate)

### KV Rune (Optional)
```
KV[CAP=<0.0-1.0>,POLICY=<LRU|WINDOW|TASK_BOUND>,PURGE=<ON_STRESS|ON_EVENT|ON_STRESS_OR_EVENT>]
```
- `CAP`: Fraction of total RAM for KV cache
- `POLICY`: Eviction policy
- `PURGE`: When to purge cache

### Tier Rune (Optional, default=LOCAL)
```
TIER=<LOCAL|EXTENDED|COLD>
```

### Priority Rune (Optional, default=5)
```
PRIORITY=<0-9>
```

### Degrade Path (Optional)
```
DEGRADE{
  STEP1:SHRINK_KV(0.75),
  STEP2:CONTEXT(4096),
  STEP3:DISABLE(HIGH_COST_METRICS),
  STEP4:BATCH(ASYNC),
  STEP5:OFFLOAD(EXTENDED)
}
```

Supported degradation actions:
- `SHRINK_KV(fraction)` - Reduce KV cache size
- `CONTEXT(tokens)` - Limit context window
- `DISABLE(feature)` - Disable optional features
- `BATCH(mode)` - Change batching strategy
- `OFFLOAD(tier)` - Offload to different memory tier

## RAM Stress Monitoring

The system continuously monitors `/proc/meminfo` to compute a RAM stress scalar:

- **0.0** - No stress (plenty of memory)
- **0.25** - Low stress
- **0.50** - Moderate stress
- **0.75** - High stress
- **1.0** - Critical stress (near OOM)

Degradation activates when:
```
RAM_STRESS > (0.3 + 0.05 * priority)
```

Higher priority jobs degrade later.

## Testing

Run the test suite:

```bash
python -c "import sys; sys.path.insert(0, '.'); from tests.test_memory_runes import *; test_parse_mem_rune_basic(); test_parse_kv_rune_basic(); test_parse_full_profile(); test_ram_stress_range(); print('All tests passed!')"
```

Or run the example:

```bash
PYTHONPATH=/home/user/AAL-core python examples/memory_governance_example.py
```

## Integration with Your Pipeline

The memory governance layer sets degradation parameters in `job.metadata`. Your LLM/pipeline code should consume these:

```python
def run_job(job: JobContext):
    # Apply KV shrinking
    if "kv_shrink_factor" in job.metadata:
        kv_cache.resize(base_size * job.metadata["kv_shrink_factor"])

    # Limit context window
    if "max_context_tokens" in job.metadata:
        context_limit = job.metadata["max_context_tokens"]

    # Disable features
    if "disabled_features" in job.metadata:
        for feature in job.metadata["disabled_features"]:
            disable_feature(feature)

    # Change batch mode
    if "batch_mode" in job.metadata:
        set_batch_mode(job.metadata["batch_mode"])

    # Offload to different tier
    if "offload_tier" in job.metadata:
        offload_to(job.metadata["offload_tier"])
```

## AAL-Core Overlay Bus

AAL-Core also provides an overlay invocation bus with append-only provenance logging:

### Starting the Bus

```bash
uvicorn main:app --reload
```

### Invoking an Overlay

```bash
curl -X POST "http://127.0.0.1:8000/invoke/abraxas" \
  -H "Content-Type: application/json" \
  -d '{"phase":"OPEN","data":{"prompt":"hello","intent":"test"}}' | jq .
```

### Provenance & Replay

All invocations are logged to `logs/provenance.jsonl` with SHA256 payload hashing.

**Enable Dev Mode (logs full payload for exact replay):**
```bash
export AAL_DEV_LOG_PAYLOAD=1
```

**Replay a provenance event:**
```bash
python3 TOOLS/replay.py 1  # Replay line 1
```

**View provenance log:**
```bash
tail -n 10 logs/provenance.jsonl | jq .
```

### Overlay Structure

Overlays are located in `.aal/overlays/{name}/`:
- `manifest.json` - Metadata, phases, capabilities, timeout
- `src/run.py` - Executable that reads JSON from stdin, writes to stdout

**Examples:**
- `.aal/overlays/abraxas/` - Analysis-only overlay (phases: OPEN, ALIGN, CLEAR, SEAL)
- `.aal/overlays/abraxas_exec/` - Exec-capable overlay (adds ASCEND phase with 'exec' capability)

### Capability Enforcement

Overlays declare capabilities in their manifest:
- `analysis` - Read-only analysis operations (CLEAR phase)
- `exec` - Execution operations (ASCEND phase)

The bus enforces that overlays can only use phases declared in their manifest. This provides defense-in-depth against capability escalation.

## Next Steps

1. Wire your LLM/pipeline to respect `job.metadata` parameters
2. Add cgroup/container enforcement for `hard_cap_mb`
3. Implement tier-specific memory allocators (LOCAL/EXTENDED/COLD)
4. Add metrics collection for RAM_STRESS vs degradation effectiveness
5. Tune degradation thresholds based on workload characteristics
6. Add overlay capability enforcement (block writes in CLEAR phase)

## Jetson Orin Nano prep (post-flash, pre-brainstem)

This bootstrap readies AAL-Core on a freshly flashed Orin Nano before loading brainstem:

1. Clone the repo on the device and run the prep script (installs system deps, builds a venv, installs Python deps, writes a systemd unit template):
   ```bash
   cd ~/AAL-core
   # Optional env: VENV_DIR=</path>, SERVICE_NAME=aal-core, AAL_PORT=8000, RUN_TESTS=1
   bash TOOLS/orin_nano_prep.sh
   ```
2. Install the generated service for auto-start (defaults to port 8000 and AAL_DEV_LOG_PAYLOAD=0):
   ```bash
   sudo cp TOOLS/aal-core.service /etc/systemd/system/aal-core.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now aal-core.service
   ```
3. Validate the bus:
   ```bash
   curl http://localhost:8000/
   curl http://localhost:8000/overlays
   tail -n 5 logs/provenance.jsonl  # after an invoke
   ```
4. When brainstem is ready to attach, point it at the service host/port above; set `AAL_DEV_LOG_PAYLOAD=1` in the unit if you want full payload replay logging.

---

## Overlays

AAL-Core includes a **hot-swappable overlay adapter layer** that allows external services (BeatOven, Psy-Fi, Patch-Hive, HollerSports, etc.) to integrate with the memory governance spine without library dependencies.

### Architecture

```
aal_overlays/
├── manifest.py       # Overlay schema & validation
├── registry.py       # Install/enable/disable overlays
├── dispatch.py       # Integration seam with MemoryAwareScheduler
├── provenance.py     # Deterministic run_id & tracking
└── runners/
    ├── http_runner.py   # HTTP-based overlays
    └── proc_runner.py   # Subprocess-based overlays
```

### Key Concepts

- **Overlay**: External capability (service or CLI) with a manifest
- **Manifest**: JSON file defining entrypoints, capabilities, memory profiles, and policies
- **Registry**: Manages installed/enabled overlays
- **Dispatch**: Creates JobContext + submits through MemoryAwareScheduler
- **Provenance**: Deterministic tracking with run_id, hashes, environment fingerprint

### Quick Start

#### 1. Create an Overlay Manifest

```python
from aal_overlays import OverlayManifest

manifest_data = {
    "name": "psyfi",
    "version": "0.1.0",
    "description": "Psy-Fi simulation overlay",
    "entrypoints": {
        "http": {"base_url": "http://127.0.0.1:8787"}
    },
    "capabilities": {
        "simulate": {
            "runner": "http",
            "path": "/run",
            "method": "POST",
            "timeout_s": 60,
            "default_profile": "BALANCED",
            "degradation": {
                "max_fraction": 0.7,
                "disable_nonessential": true
            }
        }
    },
    "resources": {"prefers_gpu": true},
    "policy": {"deterministic": true}
}

manifest = OverlayManifest.from_dict(manifest_data)
```

#### 2. Install and Enable

```python
from aal_overlays import OverlayRegistry

registry = OverlayRegistry()  # Uses .aal/overlays by default
registry.install_manifest(manifest)
registry.enable("psyfi")
```

#### 3. Dispatch Capability Calls

```python
from abx_runes.scheduler_memory_layer import MemoryAwareScheduler
from aal_overlays import dispatch_capability_call, make_overlay_run_job

# Create scheduler with overlay runner
run_job = make_overlay_run_job(registry)
scheduler = MemoryAwareScheduler(run_job)

# Execute capability
result = dispatch_capability_call(
    scheduler=scheduler,
    registry=registry,
    capability="psyfi.simulate",
    payload={
        "simulation_type": "quantum_coherence",
        "parameters": {"duration": 100}
    },
    profile="BALANCED",  # Optional; uses capability default if omitted
    seed="fixed-seed"    # Optional; for deterministic run_id
)

print(result["ok"])          # True/False
print(result["result"])      # Capability output
print(result["provenance"])  # Run tracking
```

### Manifest Structure

Manifests are stored at `.aal/overlays/<overlay_name>/manifest.json`:

```json
{
  "name": "overlay_name",
  "version": "0.1.0",
  "description": "...",
  "entrypoints": {
    "http": {"base_url": "http://..."},
    "proc": {"command": ["python", "-m", "cli"]}
  },
  "capabilities": {
    "capability_name": {
      "runner": "http",
      "path": "/endpoint",
      "method": "POST",
      "timeout_s": 30,
      "default_profile": "BALANCED",
      "degradation": {
        "max_fraction": 0.5,
        "disable_nonessential": true
      }
    }
  },
  "resources": {
    "prefers_gpu": false,
    "notes": "Optional notes"
  },
  "policy": {
    "deterministic": true
  }
}
```

### Memory Profiles

Three built-in profiles are available:

- **MINIMAL**: 512-1024MB, priority 3, LOCAL tier
- **BALANCED**: 2-4GB, priority 5, EXTENDED tier, KV cache + degradation
- **PERFORMANCE**: 4-8GB, priority 8, LOCAL tier, minimal degradation

You can also provide custom rune text as the `profile` parameter.

### Provenance Tracking

Every dispatch generates a deterministic `ProvenanceRecord`:

```python
{
  "run_id": "sha256_hash",
  "overlay": {"name": "psyfi", "version": "0.1.0"},
  "capability": "simulate",
  "payload_hash": "sha256_of_payload",
  "environment": {
    "python_version": "3.11.0",
    "platform": {"system": "Linux", "release": "..."},
    "git_commit": "abc123...",
    "timestamp_utc": "2025-12-14T12:00:00Z"
  },
  "deterministic": true,
  "seed": "optional_seed"
}
```

### HTTP Runner

Uses `urllib.request` (no external deps):
- Deterministic JSON encoding (`sort_keys=True`)
- Automatic retries (2 attempts with exponential backoff)
- Timeout enforcement
- Standard response format: `{"ok": bool, "result": ..., "error": ...}`

### Proc Runner

Executes CLI overlays via subprocess:
- Command: `base_command + [path, "--stdin-json"]`
- Request sent via stdin as canonical JSON
- Response read from stdout as JSON

### Testing

Run the test suite:

```bash
# Test manifests
python tests/test_overlay_manifest.py

# Test registry
python tests/test_overlay_registry.py

# Test HTTP dispatch (includes fake server)
python tests/test_overlay_dispatch_http.py
```

Run the example:

```bash
python examples/overlay_call_example.py
```

### Integration Pattern

The overlay layer integrates seamlessly with the existing memory governance:

1. **Dispatch** resolves capability → creates JobContext with memory profile
2. **MemoryAwareScheduler** applies degradation based on RAM_STRESS
3. **Runner** executes via HTTP/proc with degraded parameters in `job.metadata`
4. **Overlay service** reads degradation hints and adjusts behavior

This architecture allows:
- **Zero coupling**: Overlays don't import AAL-Core
- **Hot swap**: Enable/disable overlays without restarts
- **Memory safety**: All overlays governed by ABX-Runes constraints
- **Provenance**: Every call tracked with deterministic run_id

### Deployment Example

1. **Deploy overlay service** (e.g., Psy-Fi on port 8787)
2. **Create manifest** with service URL
3. **Install to registry**: `registry.install_manifest(manifest)`
4. **Enable**: `registry.enable("psyfi")`
5. **Dispatch calls**: Memory-governed execution with automatic degradation

### Next Steps

1. Deploy your overlay as an HTTP service or CLI
2. Write a manifest describing its capabilities
3. Install and enable in registry
4. Use `dispatch_capability_call()` for memory-safe execution
5. Monitor provenance records for debugging and audit

## License

See [LICENSE](LICENSE) file.
