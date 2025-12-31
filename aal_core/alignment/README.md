# AAL Alignment Package

Multi-layered alignment and containment system for AI agents, from LLMs to AGI-adjacent capabilities.

## Quick Start

```python
from aal_core.alignment import get_governor, ContainmentRegime

# Initialize the governor
governor = get_governor()

# Register an agent
governor.register_agent(
    agent_id="my_agent",
    regime=ContainmentRegime.BOXED,
    human_approver="admin"
)

# Validate actions
allowed, reason = governor.validate_action(
    agent_id="my_agent",
    action_type="execute_code",
    action_data={"requires_tool": "code_execution"}
)

# Scan outputs
clean = governor.scan_agent_output(
    agent_id="my_agent",
    output_text="Here's my analysis..."
)
```

## Components

### Regimes (`regimes.py`)
Three containment levels: LAB (deep isolation), BOXED (sandboxed), FIELD (constrained deployment)

### Capability Graph (`capability_graph.py`)
Track and constrain what agents can do. Prevent unauthorized capability compositions.

### Objective Firewall (`objective_firewall.py`)
Control what agents can optimize for. Block misaligned goals.

### Tripwires (`tripwires.py`)
Detect alignment drift via behavioral, internal state, and infrastructure monitoring.

### Self-Modification Gateway (`selfmod_gateway.py`)
Control agent evolution. No live self-improvement without testing and approval.

### Governor (`governor.py`)
Top-level coordinator. All agent actions flow through here.

## Documentation

See `/docs/ALIGNMENT.md` for complete documentation.

## Configuration

Alignment settings in `aal_core/config.yaml`:

```yaml
alignment:
  enabled: true
  default_regime: boxed
  tripwires:
    behavioral:
      enabled: true
  self_modification:
    require_human_approval: true
```

## Design Principles

1. **Defense in Depth** - Multiple overlapping layers
2. **Fail Closed** - Deny by default
3. **Audit Everything** - Comprehensive logging
4. **Human in Loop** - Critical decisions require approval
5. **Scalable** - Works for LLMs now, AGI later
