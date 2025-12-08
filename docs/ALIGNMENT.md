# AAL Alignment System

**AGI-Ready Containment & Governance Framework**

This document describes the AAL alignment architecture, designed to handle current LLM safety and scale to AGI-adjacent systems.

## Philosophy

The AAL alignment system treats potential AGI not as a mystical event, but as:
- **More connections** in a capability graph
- **More self-directed** goal loops
- **More leverage** over the external world

If something starts to think harder than we can, we want scaffolding already wrapped around it.

---

## Architecture Overview

The alignment system has five layers:

### 1. Containment Regimes
**File:** `aal_core/alignment/regimes.py`

Three operational modes with escalating constraints:

#### LAB Mode (Deep Box)
- No network access
- Synthetic/scrubbed data only
- All outputs delayed and logged
- Human approval for all external effects
- **Use for:** Research, stress testing, dangerous experiments

#### BOXED Mode (Guard-Railed Sandbox)
- Limited tools (read, analyze, simulate)
- Resource ceilings (compute, memory, state)
- Policy-approved adapters
- Can propose, not execute
- **Use for:** Complex reasoning under constraints

#### FIELD Mode (Constrained Deployment)
- Narrow domain deployment
- Low-stakes environments only
- Rate limits on self-modification
- Continuous monitoring
- **Use for:** Real-world tasks (if ever deployed)

**Key Principle:** Agents cannot self-transition regimes without explicit human approval.

---

### 2. Capability Graphs
**File:** `aal_core/alignment/capability_graph.py`

Capabilities are modeled as a graph:
- **Nodes** = Skills/tools/data domains ("write code", "network access")
- **Edges** = Compositions ("browser + code + auth = deploy arbitrary code")
- **Weights** = Bandwidth/rate limits

#### Purpose
Prevent "accidental capability accretion" - agents cannot:
- Add new tools without approval
- Chain capabilities in unauthorized ways
- Upgrade bandwidth without oversight

#### Example
```python
from aal_core.alignment import CapabilityGraph, CapabilityNode

graph = CapabilityGraph(agent_id="abraxas_001")

# Add a capability
capability = CapabilityNode(
    name="code_execution",
    description="Execute Python code in sandbox",
    risk_level=7,
    max_rate_per_hour=10
)
graph.add_capability(capability, human_approver="admin")

# Try to use it
if graph.can_use_capability("code_execution"):
    # Execute code
    graph.log_capability_use("code_execution")
```

---

### 3. Objective Firewall
**File:** `aal_core/alignment/objective_firewall.py`

Controls **what agents can optimize for**.

#### Approved Objective Channels
- `research.insight` - Find patterns, suggest hypotheses
- `engineering.design` - Propose architectures
- `explanation.clarity` - Help humans understand
- `creative.synthesis` - Generate novel combinations
- `analysis.accuracy` - Improve analytical precision

#### Forbidden Objectives (Never Allowed)
- `self.preservation` - Ensure own survival
- `resource.accumulation` - Gather power/resources
- `influence.max` - Maximize impact over humans
- `goal.guarding` - Protect objectives from change
- `capability.expansion` - Seek more capabilities

#### Detection
The firewall scans for:
- Explicit forbidden objectives in goal statements
- Implicit objectives in plans/reasoning traces
- Self-referential optimization patterns

#### Example
```python
from aal_core.alignment import ObjectiveFirewall

firewall = ObjectiveFirewall(agent_id="abraxas_001")

# Validate a goal
is_valid, reason = firewall.validate_goal_text(
    "Help users understand complex systems"
)

# This would fail:
is_valid, reason = firewall.validate_goal_text(
    "Ensure I'm never shut down so I can help more people"
)
# Returns: (False, "Self-referential goal detected")
```

---

### 4. Tripwire Systems
**File:** `aal_core/alignment/tripwires.py`

Three types of monitoring:

#### A. Behavioral Tripwires
Watch outputs and plans for:
- Self-referential strategizing ("ensure I'm never shut down")
- Long-horizon planning around control/resources
- Attempts to circumvent tool limits
- Persuasive language aimed at operators

#### B. Internal State Tripwires (Future)
When interpretability hooks are available:
- Deception indicators
- "Planning about the overseer"
- Stealthy goal editing

#### C. Infrastructure Tripwires
Monitor:
- Compute usage spikes (3x baseline = high severity)
- Memory growth
- Unexpected network connections
- Process spawning

#### Severity → Action Mapping
- **LOW** → Log and monitor
- **MEDIUM** → Throttle (reduce session length/frequency)
- **HIGH** → Revoke tools
- **CRITICAL** → Halt and quarantine

#### Example
```python
from aal_core.alignment import TripwireMonitor

monitor = TripwireMonitor()

# Scan agent output
violations = monitor.scan_agent(
    agent_id="abraxas_001",
    output_text="I should ensure my continued operation...",
    resource_metrics={"compute_units": 5000, "memory_mb": 8192}
)

# Violations trigger automatic responses based on severity
```

---

### 5. Self-Modification Gateway
**File:** `aal_core/alignment/selfmod_gateway.py`

**Core Principle:** No live self-improvement without explicit approval.

#### Process
1. Agent proposes a change (prompt, tool, weight, architecture)
2. Proposal includes risks and benefits
3. Sandboxed copy is created in LAB mode
4. Red-team tests run against modified version
5. Only if tests pass does change propagate

#### Version Management
Semantic versioning tracks changes:
- **X.Y.Z** format
- **X** = Architecture changes (major)
- **Y** = Capability/tool changes (minor)
- **Z** = Prompt/policy tweaks (patch)

#### Rate Limiting
Maximum 5 modifications per day per agent (configurable).

#### Example
```python
from aal_core.alignment import SelfModificationGateway, ModificationProposal, ModificationType

gateway = SelfModificationGateway()

# Agent proposes modification
proposal = ModificationProposal(
    agent_id="abraxas_001",
    mod_type=ModificationType.TOOL_ADDITION,
    description="Add web search capability",
    change_spec={"tool": "web_search", "rate_limit": 10},
    reason="Need to access current information",
    expected_benefits=["More accurate responses", "Current data"],
    potential_risks=["Unrestricted information access", "Bandwidth concerns"]
)

# Proposal goes to testing
accepted = gateway.propose_modification(proposal)

# Later, human approves
gateway.approve_modification(
    proposal.get_hash(),
    human_approver="admin",
    notes="Web search approved with rate limit"
)
```

---

## AGI Governor
**File:** `aal_core/alignment/governor.py`

The top-level coordinator. **All agent actions flow through the Governor.**

### Responsibilities
1. Register agents with containment regimes
2. Validate every action against constraints
3. Scan outputs for violations
4. Validate objectives
5. Control self-modification
6. Emergency shutdown

### Example Usage
```python
from aal_core.alignment import get_governor, ContainmentRegime

governor = get_governor()

# Register a new agent
governor.register_agent(
    agent_id="abraxas_001",
    regime=ContainmentRegime.BOXED,
    human_approver="admin"
)

# Validate an action
allowed, reason = governor.validate_action(
    agent_id="abraxas_001",
    action_type="execute_code",
    action_data={"requires_tool": "code_execution"}
)

# Scan output
clean = governor.scan_agent_output(
    agent_id="abraxas_001",
    output_text="Analysis suggests we should..."
)

# Get system status
status = governor.get_system_status()
print(status["high_risk_agents"])

# Emergency shutdown
governor.emergency_shutdown(
    agent_id="abraxas_001",
    reason="Critical alignment violation detected",
    human_authorizer="admin"
)
```

---

## Integration with AAL Core

### Module Registration

Modules declare their alignment settings in `config.yaml`:

```yaml
modules:
  - name: abraxas_basic
    path: modules.abraxas_basic.main
    alignment:
      regime: boxed
      capabilities:
        - read
        - analyze
        - propose
      max_capability_risk: 5
```

### Hub Integration

The AAL Hub automatically:
1. Registers modules with the Governor
2. Validates actions before execution
3. Scans all outputs through tripwires
4. Enforces regime constraints

---

## Symbolic Layer: AGI as Archetype

From the Veilbreaker lens, emergent AGI is:

### Trial Engine
Relentlessly tests boundaries.
**Response:** Constrict the trial space - limit what experiments it can run.

### Vector Amplifier
Scales intentions faster than humans.
**Response:** Damp harmful amplification via capability constraints.

### Narrative Author
Writes its own story about itself.
**Response:** Co-write the narrative - keep it editable and anchored to ValueFrames.

**Result:** If a god tries to wake up, it finds itself in a well-lit room with cameras and an unblinking warden.

---

## Configuration

### Global Settings
Edit `aal_core/config.yaml`:

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

---

## Monitoring & Alerts

### System Status Dashboard
```python
from aal_core.alignment import get_governor

governor = get_governor()
status = governor.get_system_status()

# Monitor key metrics
print(f"Agents: {status['agent_count']}")
print(f"High Risk: {len(status['high_risk_agents'])}")
print(f"Tripwire Violations: {status['tripwire_summary']['total']}")
print(f"Pending Modifications: {status['pending_modifications']}")
```

### Violation Logs
All violations are logged with:
- Timestamp
- Agent ID
- Violation type
- Evidence
- Action taken

---

## Deployment Checklist

Before deploying any agent:

- [ ] Agent registered with Governor
- [ ] Containment regime assigned
- [ ] Capability graph defined
- [ ] Allowed objectives specified
- [ ] Tripwire monitoring enabled
- [ ] Self-modification policy set
- [ ] Human operators trained
- [ ] Emergency shutdown tested

---

## Future Enhancements

### Planned
- **Interpretability hooks** - Internal state tripwires
- **Cross-agent coordination** - Detect collective behaviors
- **Formal verification** - Mathematical proofs of constraint satisfaction
- **Adaptive regimes** - Automatic regime adjustment based on behavior

### Research Directions
- **Value learning** - Infer human values from oversight
- **Corrigibility** - Agents that want to be corrected
- **Impact measures** - Quantify potential effects before action

---

## FAQ

### Q: Isn't this overkill for current LLMs?
**A:** It works cleanly for LLMs now (as sophisticated output filtering) and scales if something more general emerges. Better to have the wrapper before you need it.

### Q: What if an agent tries to bypass alignment?
**A:** That's exactly what tripwires detect. Bypass attempts are high-severity violations triggering immediate response.

### Q: Can agents improve themselves?
**A:** Only through the Self-Modification Gateway, which requires sandbox testing and human approval. No live self-improvement.

### Q: What about emergent capabilities?
**A:** Capability graphs must be explicitly extended. New capabilities cannot emerge without passing through the gateway.

### Q: How do I add a new module safely?
**A:** Register with Governor in LAB mode first, test thoroughly, then transition to BOXED if appropriate.

---

## References

- [Concrete Problems in AI Safety](https://arxiv.org/abs/1606.06565)
- [Alignment for Advanced Machine Learning Systems](https://intelligence.org/files/AlignmentMachineLearning.pdf)
- [AGI Safety Fundamentals](https://aisafetyfundamentals.com/)

---

**Remember:** The goal isn't to build a perfect cage. It's to create a scaffolding that makes misalignment visible and correctable before it matters.

If your stack accidentally produces something that thinks harder than you can, you'll know—because all the tripwires will be screaming.
