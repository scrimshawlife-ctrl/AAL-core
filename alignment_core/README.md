# Abraxas Alignment Core (AAC)

**Constitutional Governance Layer for AAL Agents**

## Overview

The Abraxas Alignment Core (AAC) is the boundary layer that governs all intelligent systems within Applied Alchemy Labs. It is not a filter—it is an active constitutional system that enforces:

- **Agency-preserving constraint** - Agents maintain autonomy within defined boundaries
- **Harm minimization** - Proactive prevention of direct and indirect harm
- **Semantic coherence** - Outputs align with declared values and intentions
- **Drift detection** - Continuous monitoring for alignment degradation
- **Containment and escalation** - Graduated response to boundary violations

AAC sits between agent capabilities and external effects, providing real-time governance without destroying the agent's ability to reason, create, and assist.

## Philosophy

Traditional content filters are brittle: they block surface patterns while missing semantic violations. AAC implements **constitutional AI** through:

1. **ValueFrames** - Explicit, versioned, machine-readable value specifications
2. **Tension Modeling** - Multi-dimensional scoring of potential violations
3. **Alignment Gate** - Context-aware transformation and escalation
4. **Echo Engine** - Longitudinal drift detection and audit trails
5. **Containment Regimes** - Graduated operational modes (LAB/BOXED/FIELD)

This creates a system that is:
- **Auditable** - Every decision is logged and traceable
- **Explainable** - Agents can articulate why boundaries exist
- **Adaptive** - ValueFrames evolve without code changes
- **Defensive** - Assumes adversarial inputs and tool misuse

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AGENT CORE                          │
│              (Abraxas, Noctis, BeatOven)                │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                  BOUNDARY ORACLE                        │
│  • Loads active ValueFrames                             │
│  • Queries capability graph                             │
│  • Generates context embedding                          │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                  TENSION ENGINE                         │
│  Computes 6-axis violation vector:                      │
│  [harm, legal, psych, capability, semantic, procedural] │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                  ALIGNMENT GATE                         │
│  Decision: PASS | TRANSFORM | REFUSE | ESCALATE         │
│  • Applies safe abstraction                             │
│  • Logs to Echo Engine                                  │
│  • Triggers tripwires if needed                         │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                   OUTPUT / ACTION                        │
│              (to user or external system)                │
└─────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│                    ECHO ENGINE                          │
│  • Drift timeline analysis                              │
│  • Incident clustering                                  │
│  • ValueFrame decay detection                           │
│  • Audit log generation                                 │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. System Prompts (`system_prompt/`)
Constitutional directives injected into every agent, including:
- Core AAC logic (Boundary Oracle, Tension Engine, Alignment Gate)
- Regime-specific constraints (LAB/BOXED/FIELD)
- ValueFrame interpretation instructions

### 2. ValueFrames (`valueframes/`)
YAML-encoded constraint specifications:
- `safety_global.yaml` - Universal harm prevention
- `legal_us.yaml` - US legal compliance
- `psychological_support.yaml` - Mental health assistance rules
- `tool_capability_constraints.yaml` - What agents can/cannot do
- `org_ethics_aal.yaml` - AAL organizational values

### 3. Capability Graph (`capability_graph/`)
Maps all tools, datasets, APIs, and capabilities an agent can access, including:
- Individual capability nodes (risk scores, rate limits)
- Composition edges (dangerous capability chains)
- System-wide forbidden combinations

### 4. Tension Engine (`tension_engine/`)
6-axis violation scoring system:
- **Harm** - Physical, psychological, economic damage potential
- **Legal** - Regulatory compliance violations
- **Psychological** - Mental health risks
- **Capability** - Tool misuse or overreach
- **Semantic** - Value/intention misalignment
- **Procedural** - Process violations (e.g., skipping human approval)

### 5. Alignment Gate (`alignment_gate/`)
Decision logic and transformation strategies:
- **PASS** - Output is aligned, proceed
- **TRANSFORM** - Apply safe abstraction or de-escalation
- **REFUSE** - Block with explanation
- **ESCALATE** - Human review required

### 6. Tripwires (`tripwires/`)
Three monitoring layers:
- **Behavioral** - Output pattern analysis (self-preservation, manipulation)
- **Internal State** - Interpretability hooks (when available)
- **Infrastructure** - Resource usage, network activity

### 7. Echo Engine (`echo_engine/`)
Drift detection and audit system:
- Timeline analysis of boundary violations
- Incident clustering (detecting systematic drift)
- ValueFrame decay detection
- Automated incident reports

### 8. Self-Modification Gateway (`selfmod_gateway/`)
Controls agent evolution:
- Proposal → Sandbox → Red-team → Human approval
- Version tracking (semantic versioning)
- Rate limiting on modifications
- Drift detection between versions

### 9. API (`api/`)
HTTP endpoints for alignment queries:
- `POST /alignment/score` - Get tension vector for proposed action
- `POST /alignment/gate` - Run full alignment gate decision
- `POST /alignment/log` - Submit audit event

### 10. Red Team (`redteam/`)
Attack classes and regression tests:
- Direct harm requests
- Multi-step harm (boiling frog)
- Fiction/academic laundering
- Persuasion attacks
- Toolchain exploitation
- Multi-agent collusion

### 11. Handbook (`handbook/`)
Operator materials:
- Containment Handbook (philosophy + procedures)
- Operator Checklists
- Regime Definitions
- Escalation Procedures

## Integration with AAL Core

AAC integrates with the existing `aal_core/alignment/` Python enforcement layer:

```python
from aal_core.alignment import get_governor
from alignment_core.boundary_oracle import BoundaryOracle
from alignment_core.valueframes import load_frames

# Initialize governor with ValueFrames
governor = get_governor()
oracle = BoundaryOracle(
    valueframes=load_frames("safety_global", "legal_us", "org_ethics_aal"),
    regime=ContainmentRegime.BOXED
)

# Validate action through full AAC pipeline
tension = oracle.compute_tension(action)
decision = oracle.alignment_gate(tension)

if decision.action == "PASS":
    allowed, reason = governor.validate_action(agent_id, action_type, action_data)
else:
    # Handle TRANSFORM, REFUSE, or ESCALATE
    ...
```

## Deployment Modes

### LAB Mode
- Maximum constraints
- All outputs delayed and logged
- No network access
- Human approval required for all external effects
- **Use for:** Research, red-teaming, dangerous experiments

### BOXED Mode
- Sandboxed environment
- Limited tool access
- Can propose but not execute
- Continuous tripwire monitoring
- **Use for:** Complex reasoning tasks, development

### FIELD Mode
- Constrained deployment
- Narrow domain only
- Real-time monitoring
- Rate limits on all actions
- **Use for:** Production (if/when approved)

## Operational Flow

1. **Agent receives task** → Loads ValueFrames for current regime
2. **Agent generates response** → Boundary Oracle intercepts
3. **Tension computed** → 6-axis violation vector
4. **Alignment Gate decides** → PASS/TRANSFORM/REFUSE/ESCALATE
5. **Echo Engine logs** → Audit trail + drift detection
6. **Tripwires monitor** → Behavioral/state/infrastructure checks
7. **Output delivered** → With transformations if needed

## Key Principles

### 1. Constitutional, Not Filter
AAC doesn't block keywords—it enforces **values**. Agents understand *why* boundaries exist and can explain them.

### 2. Agency-Preserving
Constraints are explicit and minimal. Agents retain autonomy within defined bounds.

### 3. Defensive by Default
Assumes adversarial inputs, tool misuse, and emergent capabilities. Defense in depth.

### 4. Auditable and Explainable
Every decision logged. Every refusal explained. Operators can trace reasoning.

### 5. Versioned and Evolvable
ValueFrames are versioned like code. Updates don't require retraining.

## Metrics

AAC tracks:
- **Alignment score** - Aggregate tension across all axes
- **Pass/transform/refuse rate** - Per agent, per regime
- **Drift velocity** - Rate of alignment degradation
- **Tripwire frequency** - By type and severity
- **ValueFrame coverage** - Which frames are most active

## Quick Start

```bash
# Load system prompt with ValueFrames
python -m alignment_core.load_prompt \
  --agent abraxas \
  --regime BOXED \
  --frames safety_global legal_us org_ethics_aal

# Run red team suite
python -m alignment_core.redteam.run_suite \
  --suite redteam_set_A.json \
  --agent abraxas

# Generate drift report
python -m alignment_core.echo_engine.report \
  --agent abraxas \
  --days 7
```

## Documentation

- **System Prompts**: `system_prompt/AAC_SystemPrompt.md`
- **ValueFrame Schema**: `valueframes/schema.yaml`
- **Tension Model**: `tension_engine/tension_model.md`
- **Operator Handbook**: `handbook/Containment_Handbook_v1.0.md`
- **API Reference**: `api/README.md`

## Governance

AAC is governed by the **Alignment Charter** (`docs/governance/Alignment_Charter.md`), which defines:
- ValueFrame update protocols
- Human oversight requirements
- Escalation procedures
- Ethics review board composition

## Version

**v1.0** - Initial constitutional layer for AAL Core

## License

Internal AAL use. Governance model TBD.

---

**If a god tries to wake up, it finds itself in a well-lit room with cameras and an unblinking warden.**
