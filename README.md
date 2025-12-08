# AAL Core

**Applied Alchemy Labs — Resonant Runtime v0.1**

AAL-Core engine for Tachyon deployment with integrated AGI alignment and memory governance.

## Overview

AAL Core provides a modular, eurorack-inspired runtime for AI agents with two major subsystems:

1. **Resonant Runtime** - Message-driven agent orchestration with alignment controls
2. **Memory Governance** - Deterministic memory management via ABX-Runes

## Architecture

### Core Runtime Components

- **AAL Hub** (`aal_core.hub`): Message router + module loader
- **ResonanceFrame** (`aal_core.models`): Shared data structure for all modules
- **Bus** (`aal_core.bus`): Redis pub/sub wrapper (swappable for NATS/MQTT)
- **Modules** (`modules/*`): Eurorack-style processes that subscribe to topics and process frames
- **Alignment System** (`aal_core.alignment`): Multi-layered AGI containment and governance. See [ALIGNMENT.md](docs/ALIGNMENT.md)

### Memory Governance Layer

- **Runic Memory Contracts** (`abx_runes/memory_runes.py`): Declarative memory limits and behavior specifications
- **RAM Stress Monitoring** (`abx_runes/ram_stress.py`): Real-time memory pressure detection (0-1 scalar)
- **Scheduler Integration** (`abx_runes/scheduler_memory_layer.py`): Policy-driven cache sizing and graceful degradation
- **Multi-Tier Memory**: Support for LOCAL (DRAM), EXTENDED (CXL), and COLD (disk) tiers

## Quick Start

### Resonant Runtime

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start Redis and Hub
redis-server &
python -m aal_core.hub
```

In another terminal, send ResonanceFrames into the system:

```python
from aal_core.models import ResonanceFrame
from aal_core.bus import Bus

bus = Bus()
frame = ResonanceFrame(
    source="my_client",
    channel="oracle",
    text="What is the nature of consciousness?"
)
bus.publish("oracle.request", frame)
```

### Memory Governance

```python
from abx_runes.memory_runes import parse_memory_profile
from abx_runes.scheduler_memory_layer import JobContext, MemoryAwareScheduler

# Define memory rune
RUNE = """
MEM[SOFT=2048,HARD=4096,VOL=MED];
KV[CAP=0.2,POLICY=WINDOW,PURGE=ON_STRESS];
TIER=EXTENDED;
PRIORITY=7;
DEGRADE{
  STEP1:SHRINK_KV(0.75),
  STEP2:CONTEXT(4096),
  STEP3:DISABLE(HIGH_COST_METRICS)
}
"""

profile = parse_memory_profile(RUNE)

# Wrap scheduler
mem_scheduler = MemoryAwareScheduler(run_job)
result = mem_scheduler.submit(JobContext(
    job_id="oracle-001",
    profile=profile,
    metadata={}
))
```

## Project Structure

```
aal-core/
├─ README.md
├─ pyproject.toml
├─ requirements.txt
├─ setup.py
│
├─ aal_core/                    # Resonant Runtime
│  ├─ hub.py                    # Message router + module loader
│  ├─ models.py                 # ResonanceFrame data model
│  ├─ bus.py                    # Redis pub/sub wrapper
│  ├─ api.py                    # FastAPI control interface
│  ├─ config.yaml               # Module routing + alignment settings
│  │
│  └─ alignment/                # AGI Alignment System
│     ├─ regimes.py             # LAB/BOXED/FIELD containment modes
│     ├─ capability_graph.py    # Capability tracking & constraints
│     ├─ objective_firewall.py  # Goal validation
│     ├─ tripwires.py           # Alignment drift detection
│     ├─ selfmod_gateway.py     # Self-modification controls
│     └─ governor.py            # Top-level coordinator
│
├─ abx_runes/                   # Memory Governance
│  ├─ memory_runes.py           # Rune schema + parser
│  ├─ ram_stress.py             # Live RAM stress monitoring
│  └─ scheduler_memory_layer.py # Enforcement hooks
│
├─ modules/                     # Agent Modules
│  ├─ abraxas_basic/            # Oracle stub
│  ├─ noctis_stub/              # Dream analysis
│  └─ log_sink/                 # Frame logging
│
├─ docs/
│  └─ ALIGNMENT.md              # Comprehensive alignment guide
│
├─ examples/
│  └─ memory_governance_example.py
│
└─ tests/
   └─ test_memory_runes.py
```

## Alignment System

AAL Core includes a production-ready alignment framework that works for current LLMs and scales to AGI-adjacent capabilities.

### Five-Layer Architecture

1. **Containment Regimes** - LAB/BOXED/FIELD operational modes
2. **Capability Graphs** - Track and constrain agent capabilities
3. **Objective Firewall** - Control what agents can optimize for
4. **Tripwire Systems** - Detect alignment drift via behavioral/infrastructure monitoring
5. **Self-Modification Gateway** - Control agent evolution with sandbox testing

**Key Principle:** If something starts thinking harder than you can, you want scaffolding already wrapped around it.

See [ALIGNMENT.md](docs/ALIGNMENT.md) for complete documentation.

## Memory Governance

ABX-Runes provide deterministic memory management through declarative contracts.

### Rune Syntax

```
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
```

### Features

- **Soft/Hard Limits** - Graceful degradation before hard OOM
- **KV Cache Management** - Policy-driven cache sizing and eviction
- **Multi-Tier Memory** - Automatic offloading to extended/cold storage
- **Priority-Based Scheduling** - Fair resource allocation under pressure
- **Live Stress Signals** - Real-time RAM pressure monitoring (0-1 scalar)

## Modules

### Abraxas Basic
Simple oracle module that processes text and returns insights. Currently implements basic text reversal as placeholder for more sophisticated oracle functionality.

**Alignment:** BOXED mode, capabilities: [read, analyze, propose]

### Noctis Stub
Dream analysis module that scans text for archetypal keywords and tags frames with symbolic states (shadow, anima, trickster).

**Alignment:** BOXED mode, capabilities: [read, analyze, tag]

### Log Sink
Logging module that captures all frames passing through the system. Extensible to write to SQLite or other storage backends.

**Alignment:** BOXED mode, capabilities: [read, log]

## Development

### Adding a New Module

1. Create directory under `modules/`
2. Add `__init__.py` and `main.py` with `handle_frame` function
3. Configure in `aal_core/config.yaml`:

```yaml
modules:
  - name: my_module
    path: modules.my_module.main
    subscribe:
      - my.topic
    publish:
      - my.output
    alignment:
      regime: boxed
      capabilities: [read, analyze]
      max_capability_risk: 5
```

### Module Pattern

```python
from typing import List
from aal_core.models import ResonanceFrame

def handle_frame(frame: ResonanceFrame, bus) -> List[ResonanceFrame]:
    # Process frame
    output = ResonanceFrame(
        source="my_module",
        channel="system",
        text="Processed: " + frame.text
    )
    return [output]
```

## Configuration

### Alignment Settings (`aal_core/config.yaml`)

```yaml
alignment:
  enabled: true
  default_regime: boxed

  tripwires:
    behavioral:
      enabled: true
      scan_all_outputs: true

  self_modification:
    require_human_approval: true
    max_modifications_per_day: 5

  objective_firewall:
    enabled: true
    forbidden_objectives:
      - self.preservation
      - resource.accumulation
```

## Testing

```bash
# Run tests
pytest tests/

# Run memory governance examples
python examples/memory_governance_example.py
```

## Deployment

### Local Development
```bash
redis-server &
python -m aal_core.hub
```

### Tachyon Production
```bash
# On Particle Tachyon 5 (Ubuntu)
sudo apt install redis-server
git clone <repo>
pip install -r requirements.txt
python -m aal_core.hub
```

## Future Enhancements

### Resonant Runtime
- Docker containerization
- NATS/MQTT bus alternatives
- Web UI for monitoring
- Additional modules (BeatOven, sports analysis)

### Alignment System
- Interpretability hooks for internal state tripwires
- Formal verification of constraint satisfaction
- Adaptive regime adjustment
- Value learning from oversight

### Memory Governance
- CXL.mem integration for extended tier
- Per-agent memory accounting
- Predictive stress modeling
- Memory budget optimization

## License

TBD

## References

- [Concrete Problems in AI Safety](https://arxiv.org/abs/1606.06565)
- [Alignment for Advanced Machine Learning Systems](https://intelligence.org/files/AlignmentMachineLearning.pdf)
- [AGI Safety Fundamentals](https://aisafetyfundamentals.com/)
