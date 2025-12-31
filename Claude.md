# Claude.md - AAL-Core Project Documentation

## Project Overview

AAL-Core (Architecture Abstraction Layer - Core) is a comprehensive system for orchestrating overlays, managing memory governance, and providing dynamic function discovery. The project integrates multiple subsystems into a cohesive platform for deploying and managing computational workloads with provenance tracking and capability enforcement.

## Repository Structure

```
AAL-core/
├── .aal/                           # Overlay definitions
│   └── overlays/
│       ├── abraxas/                # Analysis & prediction overlay
│       ├── abraxas_exec/          # Exec-capable variant
│       └── psyfi/                 # Psy-Fi simulation overlay
├── aal_core/                      # Core AAL modules
│   ├── alignment/                 # Constitutional alignment layer
│   ├── bus/                       # Event bus & orchestration
│   ├── integrations/              # External integrations (BeatOven, etc.)
│   ├── registry/                  # Function registry
│   └── services/                  # Core services
├── abraxas/                       # Abraxas overlay implementation
│   ├── oracle/                    # Oracle engine with drift tracking
│   └── runes/                     # Rune operators (SDS, IPL, ADD)
├── abx_runes/                     # ABX-Runes memory governance
├── aal_overlays/                  # Overlay adapter layer
├── alignment_core/                # Alignment system (regimes, tripwires)
├── bus/                           # Bus infrastructure
│   ├── overlay_registry.py        # Overlay manifest loading
│   ├── policy.py                  # Phase policy enforcement
│   ├── phase_policy.py           # Policy registry
│   ├── provenance.py             # Provenance logging
│   └── sandbox.py                # Sandboxed execution
├── engines/                       # Game state & normalization
│   └── game_state/               # State management with backtest
├── normalizers/                   # Sport normalizer schema
├── risk/                          # Cross-sport entropy throttle (CSET)
├── src/aal_core/                 # Source modules
│   ├── bus/                      # Frame-based bus
│   ├── runes/                    # ABX-Runes attachment
│   ├── schema/                   # Resonance frame schema
│   └── vendor/                   # Vendor lock verification
├── tests/                         # Comprehensive test suite
├── TOOLS/                         # Utility scripts
│   ├── replay.py                 # Deterministic replay
│   └── orin_nano_prep.sh        # Jetson deployment
├── main.py                        # FastAPI bus server
├── README.md                      # User documentation
├── CANON.md                       # Architectural changelog
└── requirements.txt               # Python dependencies
```

## Merged Branches & Features

### 1. YGGDRASIL-IR (claude/add-yggdrasil-ir-B2h3o)
- **Evidence Bundle Format**: Hash-locked provenance artifacts with CLI tooling
- **Manifest Loading**: Shared library module for deterministic loading
- **Bridge Promotion**: Shadow→forecast unlocking workflow
- **Evidence Relock**: Phase-3 rent-pay deterministic re-hashing
- **Bridge Apply Tool**: Safe patch applier for RuneLink updates
- **Unlockability Lint**: Prevents enabled bridges without keys

**Key Files**:
- `normalizers/` - Sport normalizer schema (NBA, NFL, NHL presets)
- `engines/game_state/` - GameState engine with reset, modifiers, backtest
- `risk/` - Cross-sport entropy throttle (CSET)
- `docs/runes.md` - YGGDRASIL-IR documentation

### 2. Phase Policy Enforcement (claude/add-phase-policy-enforcement-zE1qq)
- **Granular Phase Rules**: Allow/forbid external_io, writes, exec per phase
- **Capability Enforcement**: ASCEND requires explicit 'exec' capability
- **Policy Decision**: Structured policy check results with reason strings

**Key Files**:
- `bus/policy.py` - Phase policy enforcement logic
- `policies/phase_constraints.yaml` - Declarative policy definitions

### 3. BeatOven Metrics Integration (claude/beatoven-metrics-integration-kdAjo)
- **Catalog Integration**: Metrics aggregation from BeatOven service

**Key Files**:
- `aal_core/integrations/beatoven_catalog.py`

### 4. Dynamic Function Discovery (claude/dynamic-function-discovery-hTidH)
- **EventBus**: Provenance-logged event publishing
- **Function Registry**: Multi-source function aggregation
- **API Endpoints**: `/events`, `/fn/rebuild`

**Key Files**:
- `aal_core/bus.py` - EventBus implementation
- `aal_core/services/fn_registry.py` - FunctionRegistry service

### 5. Dynamic Function Registry (claude/dynamic-function-registry-tiDmM)
- **Function Descriptors**: Standardized schema with validation
- **Hash-based Change Detection**: SHA256 catalog versioning
- **Deduplication**: ID-based dedup with last-wins strategy

**Key Files**:
- `aal_core/registry/` - Function registry implementation

### 6. Oracle-Runes Integration (claude/oracle-runes-integration-modVV)
- **Rune Operators**: SDS (State Diff Set), IPL (Interpolate), ADD (Aggregate Drift Detection)
- **Oracle Engine**: Drift tracking with provenance
- **Rune Gate**: Capability-based rune access control

**Key Files**:
- `abraxas/oracle/` - Oracle engine implementation
- `abraxas/runes/operators/` - Rune operator implementations
- `scripts/run_oracle_with_runes.py` - Example runner

### 7. Setup AAL-Core (claude/setup-aal-core-01T6F5YXgHtnV7iyxBaxUC1n)
- **Alignment Core**: Constitutional layer with regime prompts (BOXED, FIELD, LAB modes)
- **Capability Graph**: Hierarchical capability management
- **Objective Firewall**: Goal validation and containment
- **Sandboxed Execution**: Subprocess isolation with timeout
- **Policy Registry**: YAML-based declarative policies

**Key Files**:
- `alignment_core/` - Complete alignment system
- `aal_core/alignment/` - Alignment governor and gateway
- `bus/sandbox.py` - Sandboxed overlay execution
- `policies/` - Phase constraint policies

## Key Concepts

### Overlays
Overlays are external capabilities (services or CLI tools) that integrate with AAL-Core through manifests. Each overlay declares:
- **Phases**: Execution modes (OPEN, ALIGN, ASCEND, CLEAR, SEAL)
- **Capabilities**: Required permissions (analysis, exec, external_io, writes)
- **Entrypoint**: Execution command
- **Timeout**: Maximum execution duration
- **YGGDRASIL Schema**: Rune topology and dependencies (optional)

### Phases & Capabilities
- **OPEN**: External IO + writes allowed, exec forbidden
- **ALIGN**: External IO + writes allowed, exec forbidden
- **ASCEND**: All capabilities allowed, requires explicit 'exec' capability
- **CLEAR**: Read-only analysis, no external IO or writes
- **SEAL**: External IO forbidden, writes allowed (finalization)

### Provenance & Replay
All invocations are logged to `logs/provenance.jsonl` with:
- SHA256 payload hashing for verification
- Optional full payload logging (AAL_DEV_LOG_PAYLOAD=1)
- Deterministic replay via `TOOLS/replay.py`

### Memory Governance (ABX-Runes)
Declarative memory contracts with:
- Soft/hard caps and volatility tiers
- KV cache management with eviction policies
- Automatic degradation under RAM stress
- Multi-tier memory support (LOCAL, EXTENDED, COLD)

## Development Workflow

### Running the Bus
```bash
uvicorn main:app --reload
```

### Invoking an Overlay
```bash
curl -X POST "http://127.0.0.1:8000/invoke/abraxas" \
  -H "Content-Type: application/json" \
  -d '{"phase":"CLEAR","data":{"prompt":"test"}}'
```

### Running Tests
```bash
# All tests
python -m pytest tests/

# Specific subsystem
python -m pytest tests/test_policy_enforcement.py
```

### Replaying Provenance Events
```bash
export AAL_DEV_LOG_PAYLOAD=1  # Enable full payload logging
python TOOLS/replay.py 1       # Replay line 1 from provenance log
```

## Integration Points

### Adding a New Overlay
1. Create directory: `.aal/overlays/<name>/`
2. Write manifest: `manifest.json` with phases, capabilities, entrypoint
3. Implement entrypoint: Reads JSON from stdin, writes JSON to stdout
4. Optional: Add YGGDRASIL schema for rune topology

### Adding a New Rune Operator
1. Create operator: `abraxas/runes/operators/<name>.py`
2. Implement interface: Input schema, transformation logic, output schema
3. Register in sigil: `abraxas/runes/sigils/manifest.json`
4. Add tests: `tests/test_<name>.py`

### Extending Phase Policies
1. Edit: `policies/phase_constraints.yaml`
2. Add capability constraints for new phases
3. Update: `bus/policy.py` if new enforcement logic needed

## Testing Strategy

- **Unit Tests**: Individual components (runes, normalizers, policies)
- **Integration Tests**: Overlay invocation, registry aggregation
- **Provenance Tests**: Replay consistency, hash verification
- **Policy Tests**: Capability enforcement, phase restrictions

## Deployment

### Jetson Orin Nano
```bash
cd ~/AAL-core
bash TOOLS/orin_nano_prep.sh
sudo cp TOOLS/aal-core.service /etc/systemd/system/
sudo systemctl enable --now aal-core.service
```

## Architecture Invariants

1. **Append-only provenance**: Never modify/delete provenance.jsonl
2. **Manifest immutability**: Overlay manifests are versioned and hashed
3. **Phase isolation**: Overlays cannot escalate capabilities beyond manifest
4. **Deterministic hashing**: All catalog hashes are order-independent
5. **Subprocess isolation**: Overlays execute in isolated subprocesses

## Future Directions

- **Tier-specific memory allocators**: Implement LOCAL/EXTENDED/COLD tiers
- **Distributed overlay execution**: Multi-node overlay orchestration
- **Live policy updates**: Hot-reload phase constraints without restart
- **Enhanced replay**: Support partial replay with state snapshots
- **Cross-overlay provenance**: Track data flow between overlays

## References

- **README.md**: User-facing documentation with quickstart guides
- **CANON.md**: Architectural changelog with version history
- **docs/runes.md**: YGGDRASIL-IR and rune system documentation
- **alignment_core/handbook/README.md**: Alignment system guide
