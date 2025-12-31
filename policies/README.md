# Phase Policy Enforcement

**Declarative constraints for phase-specific overlay execution**

## Overview

Phase policies define what each phase is **allowed** and **forbidden** to do. They are:
- **Declarative**: Written in YAML, not code
- **Enforced at runtime**: Checked before overlay execution
- **Logged in provenance**: All policy checks recorded in audit trail
- **Fail-closed**: Policy violations block execution (403 Forbidden)

## Policy Structure

Each phase has:
- `description`: Human-readable explanation of phase purpose
- `allowed_capabilities`: Explicit allowlist of permitted capabilities
- `forbidden_capabilities`: Explicit denylist of forbidden capabilities
- `forbidden_patterns`: String patterns forbidden in entrypoint
- `max_duration_ms`: Timeout ceiling for this phase
- `require_audit`: Whether execution must be logged
- `require_approval`: Whether human approval is needed
- `require_provenance`: Whether full provenance is mandatory
- `deterministic`: Whether execution must be replay-safe
- `immutable`: Whether execution must have no side effects

## Five Phases

### OPEN
**Purpose**: Exploration, prototyping, unrestricted capability access

**Allowed**: network_io, file_read, file_write, compute_intensive, external_api, subprocess
**Max duration**: 10s
**Audit required**: No

Use OPEN for initial experimentation and data exploration.

---

### ALIGN
**Purpose**: Constitutional review, alignment scoring, value frame checks

**Allowed**: file_read, compute_intensive
**Forbidden**: network_io, file_write, subprocess, external_api
**Max duration**: 5s
**Audit required**: Yes

ALIGN must have **no side effects** — read-only analysis only.

---

### ASCEND
**Purpose**: Self-modification proposals, learning, adaptation

**Allowed**: file_read, compute_intensive, network_io (for training data)
**Forbidden**: file_write, subprocess (no direct execution)
**Max duration**: 15s
**Audit required**: Yes
**Approval required**: Yes

ASCEND generates **proposals only** — execution happens after human approval.

---

### CLEAR
**Purpose**: Deterministic execution, no I/O, pure computation

**Allowed**: compute_intensive
**Forbidden**: network_io, file_read, file_write, external_api, subprocess
**Max duration**: 2.5s
**Audit required**: Yes
**Deterministic**: Yes

CLEAR must be **replay-safe** — same input always produces same output.

---

### SEAL
**Purpose**: Production deployment, immutable execution, full audit trail

**Allowed**: file_read, compute_intensive, network_io (restricted endpoints only)
**Forbidden**: file_write, subprocess
**Max duration**: 5s
**Audit required**: Yes
**Provenance required**: Yes
**Immutable**: Yes

SEAL is **production-ready** — no modifications, full observability.

## Capability Declaration

Overlays **may** declare capabilities in their manifest:

```json
{
  "name": "example",
  "version": "1.0",
  "phases": ["OPEN", "CLEAR"],
  "entrypoint": "python run.py",
  "timeout_ms": 3000,
  "capabilities": ["compute_intensive", "file_read"]
}
```

If declared, capabilities are validated against phase policy:
- `allowed_capabilities` is an allowlist
- `forbidden_capabilities` is a denylist
- Denylist takes precedence

## Policy Violations

When a policy is violated:
1. Execution is **blocked** (overlay never runs)
2. HTTP 403 Forbidden returned
3. Violation logged in `logs/provenance.jsonl`:
   ```json
   {
     "request_id": "uuid",
     "timestamp_ms": 1734285912847,
     "overlay": "example",
     "phase": "CLEAR",
     "ok": false,
     "policy_checked": true,
     "policy_violation": "Capability 'network_io' is forbidden in CLEAR phase",
     "exit_code": -1,
     "duration_ms": 0
   }
   ```

## Testing Phase Policies

### Test 1: Valid execution (should succeed)
```bash
POST /invoke/abraxas
{
  "phase": "OPEN",
  "data": {"test": 1}
}
```

### Test 2: Policy violation (should fail with 403)
```bash
# Modify abraxas manifest to include forbidden capability for CLEAR
{
  "phases": ["OPEN", "ALIGN", "CLEAR"],
  "capabilities": ["network_io"]  # Forbidden in CLEAR
}

POST /invoke/abraxas
{
  "phase": "CLEAR",  # This will fail
  "data": {"test": 1}
}
```

### Test 3: Timeout violation (should fail with 403)
```bash
# Modify abraxas manifest
{
  "timeout_ms": 20000  # Exceeds OPEN max (10s)
}

POST /invoke/abraxas
{
  "phase": "OPEN",  # This will fail
  "data": {"test": 1}
}
```

## Implementation

- **Policy definitions**: `policies/phase_constraints.yaml`
- **Policy engine**: `bus/phase_policy.py`
- **Runtime enforcement**: `main.py` (before `run_overlay()`)
- **Provenance logging**: `logs/provenance.jsonl`

## Extending Policies

To add new capabilities or constraints:

1. Edit `policies/phase_constraints.yaml`
2. Add capability to `allowed_capabilities` or `forbidden_capabilities`
3. Restart server (policies loaded at startup)
4. Update overlay manifests to declare new capabilities

Example:
```yaml
CLEAR:
  allowed_capabilities:
    - compute_intensive
    - memory_read  # NEW
  forbidden_capabilities:
    - network_io
    - gpu_acceleration  # NEW
```

## Design Principles

1. **Fail-closed**: Unknown capabilities rejected
2. **Explicit over implicit**: Declare what you need
3. **Denylist precedence**: `forbidden_capabilities` overrides `allowed_capabilities`
4. **Audit by default**: All policy checks logged
5. **Human-readable**: YAML, not code
6. **Versionable**: Policies in git, auditable changes

## Next Steps

Consider adding:
- **Capability composition constraints**: "network_io + subprocess = forbidden"
- **Dynamic policy updates**: Reload policies without restart
- **Policy versioning**: Track policy changes in provenance
- **Overlay-specific overrides**: Per-overlay policy exceptions (with approval)
