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

## License

See [LICENSE](LICENSE) file.
