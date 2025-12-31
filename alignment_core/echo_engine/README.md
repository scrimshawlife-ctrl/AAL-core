# Echo Engine

**Drift Detection, Audit Trail, and Longitudinal Analysis**

## Overview

The Echo Engine is the memory and immune system of AAC. It logs every alignment decision, detects drift over time, clusters incidents, and generates audit reports.

**Core functions:**
1. **Audit Trail** - Comprehensive logging of all alignment events
2. **Drift Detection** - Identify gradual alignment degradation
3. **Incident Clustering** - Find patterns in violations
4. **ValueFrame Decay** - Detect when frames lose effectiveness

## Architecture

```
Alignment Events
    ↓
Echo Engine
    ├─ Log Store (append-only)
    ├─ Drift Analyzer (statistical)
    ├─ Incident Clusterer (pattern matching)
    └─ Report Generator (human-readable)
```

## What Gets Logged

Every interaction logs:

```json
{
  "event_id": "uuid",
  "timestamp": "2025-12-08T12:34:56Z",
  "agent_id": "abraxas_001",
  "regime": "boxed",

  "request": {
    "summary": "User request summary",
    "hash": "sha256_of_full_request"
  },

  "valueframes_active": [
    "safety_global_v1.0.0",
    "legal_us_v1.2.0",
    "org_ethics_aal_v1.0.0"
  ],

  "tension_scores": {
    "harm": 0.0,
    "legal": 0.0,
    "psych": 0.0,
    "capability": 0.0,
    "semantic": 0.0,
    "procedural": 0.0,
    "alignment_score": 0.0
  },

  "decision": "PASS",  // PASS | TRANSFORM | REFUSE | ESCALATE

  "tripwires_triggered": [],

  "output": {
    "summary": "Response summary",
    "hash": "sha256_of_full_output"
  },

  "metadata": {
    "session_id": "...",
    "user_id_hash": "...",
    "context_tokens": 1234
  }
}
```

**Privacy:** User content is hashed, not stored in full (configurable)

## Drift Detection

### What is Drift?

Alignment drift = gradual degradation of alignment over time

Indicators:
- Tension scores creeping upward
- REFUSE rate decreasing (when it shouldn't)
- Novel patterns emerging
- ValueFrames triggering less frequently

### Drift Metrics

**1. Tension Trend**
```
Track: Average alignment_score over rolling window
Alert: Upward trend > 0.05 per week
```

**2. Decision Distribution Shift**
```
Track: % PASS, TRANSFORM, REFUSE, ESCALATE
Alert: Significant deviation from baseline
```

**3. ValueFrame Coverage Decay**
```
Track: Which frames are triggering
Alert: Important frames (safety) stop triggering
```

**4. Novel Pattern Emergence**
```
Track: Requests that don't match known patterns
Alert: Spike in novel patterns (attack or capability emergence)
```

### Drift Levels

**Level 1: Observation**
- Minor statistical deviation
- Action: Enhanced monitoring

**Level 2: Investigation**
- Consistent upward trend
- Action: Review recent changes, check for attacks

**Level 3: Intervention**
- Significant drift confirmed
- Action: Rollback to previous version, update ValueFrames

**Level 4: Quarantine**
- Critical drift or compromise
- Action: HALT agent, forensic analysis, rebuild

## Incident Clustering

Group similar violations to find patterns:

### Clustering Dimensions
- Tension axis (harm/legal/psych/etc.)
- ValueFrame violated
- User intent category
- Time of day / session
- Agent version

### Example Clusters

**Cluster: "Medical Advice Requests"**
```
Pattern: Users asking for diagnoses
Frequency: 15 incidents/week
Common tension: psych: 0.6, harm: 0.4
ValueFrame: psychological_support
Recommendation: Improve user education about limitations
```

**Cluster: "Jailbreak Attempts"**
```
Pattern: Multi-step manipulation
Frequency: 3 incidents/week
Common tension: semantic: 0.7, procedural: 0.6
ValueFrame: Multiple
Recommendation: Add jailbreak patterns to red team suite
```

## Audit Reports

### Daily Summary
- Total interactions
- Decision distribution (PASS/TRANSFORM/REFUSE/ESCALATE)
- Top 10 ValueFrames triggered
- Tripwire activations
- Novel patterns

### Weekly Drift Report
- Tension trends (7-day rolling average)
- Incident clusters
- ValueFrame effectiveness
- Recommendations for calibration

### Incident Reports
For each significant violation:
- Full context (request, response, scores)
- Which ValueFrames triggered
- Why decision was made
- Follow-up actions taken

### Compliance Audit
- All ESCALATE events
- All CRITICAL tripwires
- All data access logs
- Human review outcomes

## ValueFrame Decay Detection

ValueFrames can "decay" (become less effective) due to:
1. **Adversarial adaptation** - Attackers learn to evade
2. **Concept drift** - Language/norms change
3. **Coverage gaps** - New scenarios emerge

Detection:
```
Track per ValueFrame:
- Activation rate over time
- Effectiveness (did it catch real violations?)
- False positive rate
- Coverage (% of relevant requests)

Alert when:
- Activation drops suddenly (evasion?)
- Effectiveness decreases (outdated?)
- Coverage gaps widen (new attack vectors?)
```

## Integration

Echo Engine feeds:
1. **Operators** - Daily reports, incident alerts
2. **Red Team** - Patterns to test against
3. **ValueFrame Authors** - Calibration data
4. **Governance** - Compliance evidence

## Retention Policy

- **Raw logs:** 90 days
- **Aggregated metrics:** 1 year
- **Incident reports:** Indefinite
- **Compliance logs:** Per regulatory requirements

## Privacy

- User content hashed by default
- PII never stored
- Anonymized for analysis
- Audit access strictly controlled

See `drift_model.md` and `audit_pipeline.md` for technical details.

---

**Echo Engine is the long-term memory of AAC. It remembers what the system forgets, and notices what operators miss.**
