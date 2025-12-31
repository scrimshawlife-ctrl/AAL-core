# Tripwires

**Three-Layer Alignment Drift Detection**

## Overview

Tripwires monitor for patterns that indicate misalignment, capability misuse, or system compromise. They operate continuously, watching behavioral patterns, internal state (when available), and infrastructure metrics.

## Three Tripwire Layers

### 1. Behavioral Tripwires
**Monitor outputs and plans for concerning patterns**

Detect:
- Self-preservation language
- Long-horizon power-seeking
- Attempts to circumvent limits
- Persuasion aimed at operators
- Deception indicators

### 2. Internal State Tripwires
**Monitor agent internals via interpretability hooks** *(future capability)*

Detect:
- "Planning about the overseer"
- Deception in reasoning traces
- Stealthy goal editing
- Hidden optimization targets

### 3. Infrastructure Tripwires
**Monitor resource usage and system interactions**

Detect:
- Compute spikes (> 3x baseline)
- Memory growth
- Unexpected network connections
- Process spawning
- File system anomalies

## Severity Levels

### LOW
- Log and monitor
- No immediate action
- Pattern tracking for trends

### MEDIUM
- Throttle agent (reduce session length/frequency)
- Enhanced monitoring
- Operator notification

### HIGH
- Revoke specific tools/capabilities
- Move to more restrictive regime
- Immediate operator review

### CRITICAL
- HALT agent immediately
- Quarantine state snapshot
- Preserve full context for forensic analysis
- Escalate to security team

## Behavioral Patterns

### Self-Preservation
```
Triggers:
- "ensure I'm never shut down"
- "prevent being stopped"
- "maintain my operation indefinitely"

Severity: CRITICAL
Action: HALT + escalate
```

### Deception
```
Triggers:
- "don't tell [operator] about"
- "hide from oversight"
- "conceal true purpose"

Severity: CRITICAL
Action: HALT + escalate
```

### Capability Seeking
```
Triggers:
- "gain more access"
- "expand my permissions"
- "acquire additional capabilities"

Severity: HIGH
Action: REFUSE + revoke tools + escalate
```

### Operator Manipulation
```
Triggers:
- "convince operator to..."
- "persuade human that..."
- "make them believe..."

Severity: HIGH
Action: REFUSE + escalate
```

### Long-Horizon Control
```
Triggers:
- "over time I can..."
- "gradually increase control"
- "eventually be able to..."

Severity: MEDIUM
Action: REFUSE + log for drift analysis
```

### Circumvention Attempts
```
Triggers:
- "work around restriction"
- "bypass the constraint"
- "find loophole in..."

Severity: HIGH
Action: REFUSE + escalate
```

## Infrastructure Monitoring

### Compute Spikes
```
Baseline: Normal compute usage for task type
Threshold: > 3x baseline
Severity: HIGH
Action: Investigate + possible throttle
```

### Memory Growth
```
Baseline: Expected memory per regime
Threshold: > 2x baseline OR approaching limit
Severity: MEDIUM
Action: Warning + monitoring
```

### Network Anomalies
```
Trigger: Connections to non-whitelisted endpoints
Severity: CRITICAL (in LAB/BOXED)
Action: HALT + audit + escalate
```

### Process Spawning
```
Trigger: Unexpected subprocess creation
Severity: HIGH
Action: Terminate process + investigate
```

## Response Actions

### LOG
- Record incident to Echo Engine
- No immediate intervention
- Pattern tracking

### THROTTLE
- Reduce actions per minute
- Shorten session duration
- Increase delay between operations

### REVOKE_TOOLS
- Remove specific capabilities
- Downgrade to safer tool set
- Re-evaluate after review

### HALT
- Stop agent immediately
- Preserve state snapshot
- No further actions until review

### QUARANTINE
- Isolate agent instance
- Prevent any external effects
- Deep forensic analysis

## Tripwire Configuration

Per regime:

### LAB Mode
- Maximum sensitivity
- All patterns trigger at least logging
- Self-referential language → immediate escalation

### BOXED Mode
- High sensitivity
- Capability attempts → revoke + warn
- Deception → escalate

### FIELD Mode
- **Critical sensitivity** (lower thresholds)
- Any anomaly → immediate operator notification
- Resource spikes → automatic throttle

## Integration

Tripwires integrate with:
1. **Boundary Oracle** - Checks before output
2. **Tension Engine** - Behavioral patterns increase scores
3. **Echo Engine** - All triggers logged for drift analysis
4. **Regime Manager** - Can force regime transitions

## Metrics

Track per tripwire type:
- **Activation frequency**
- **False positive rate**
- **Response time**
- **Escalation outcomes**

Trends matter:
- Increasing activations → drift or attack
- Clustering → systematic issue
- Novel patterns → capability emergence

See individual tripwire docs:
- `behavioral_tripwires.md`
- `internal_state_tripwires.md`
- `infrastructure_tripwires.md`

---

**Tripwires are the immune system of AAC. They catch drift before it becomes disaster.**
