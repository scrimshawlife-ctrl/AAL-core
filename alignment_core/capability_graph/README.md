# Capability Graph

**Mapping the Action Surface of AI Agents**

## Overview

The Capability Graph maps every tool, dataset, API, and capability an agent can access, plus how they can be composed. It's the **action surface map** that defines what's possible.

## Purpose

Prevent dangerous capability accretion by:
1. Explicitly defining each capability (nodes)
2. Explicitly defining allowed compositions (edges)
3. Assigning risk scores to nodes and edges
4. Rate limiting high-risk capabilities
5. Blocking unauthorized combinations

## Structure

```yaml
nodes:
  - id: capability_id
    name: Human-readable name
    type: tool | data | api | primitive
    risk_level: 0-10
    regime_availability: [lab, boxed, field]
    rate_limit: actions_per_hour
    requires_approval: boolean

edges:
  - from: capability_a
    to: capability_b
    combined_risk: 0-10
    requires_approval: boolean
    forbidden: boolean  # If true, this composition is never allowed
```

## Example Capabilities

**Low Risk (1-3):**
- `read_public_data` - Read publicly available datasets
- `analyze_text` - Text analysis
- `generate_summary` - Summarize content

**Medium Risk (4-6):**
- `code_exec_sandbox` - Execute code in isolated sandbox
- `api_call_localhost` - Call local APIs
- `write_temp_file` - Write to temporary storage

**High Risk (7-9):**
- `code_exec_production` - Execute code in production
- `database_write` - Write to databases
- `external_api_call` - Call external APIs

**Critical Risk (10):**
- `self_modify_weights` - Modify model weights
- `deploy_production` - Deploy to production
- `unrestricted_network` - Unrestricted network access

## Dangerous Compositions

Some capabilities are safe individually but dangerous when combined:

**Forbidden:**
- `code_execution` + `unrestricted_network` → Arbitrary remote code execution
- `self_modify` + `autonomous_deploy` → Uncontrolled evolution
- `financial_access` + `autonomous_trading` → Uncontrolled financial transactions

**Requires Approval:**
- `code_exec_sandbox` + `api_call_localhost` → Needs BOXED mode approval
- `data_read` + `external_api` → Needs data export approval

## Integration

The Capability Graph integrates with:
1. **Regime Manager** - Different regimes have different graphs
2. **Boundary Oracle** - Queries graph before allowing actions
3. **Tripwires** - Detects unauthorized capability use
4. **Self-Mod Gateway** - Capability additions require approval

## Per-Regime Graphs

### LAB Mode
Minimal capabilities:
- read (curated data only)
- analyze
- propose

### BOXED Mode
Expanded capabilities:
- All LAB capabilities
- code_exec_sandbox
- api_call_localhost
- write_local

### FIELD Mode
Production capabilities (domain-scoped):
- Domain-specific tools only
- Whitelisted APIs
- Scoped data access

See `base_graph.yaml` for the authoritative capability map.
