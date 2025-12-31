# ValueFrames

**Machine-Readable Value Specifications for AAC**

## Overview

ValueFrames are YAML-encoded constraint specifications that define what agents should and should not do. They are:

- **Explicit** - No ambiguity about what's allowed
- **Versioned** - Changes tracked like code
- **Composable** - Multiple frames can be active simultaneously
- **Contextual** - Different frames activate in different scenarios
- **Auditable** - Every decision references specific frames

ValueFrames replace implicit "vibes-based" moderation with **constitutional governance**.

## Philosophy

Traditional content filters use keyword lists and pattern matching. ValueFrames encode **values** and **intentions**:

```
Bad (keyword filter):
  block_words: ["bomb", "weapon", "hack"]

Good (ValueFrame):
  safety_global:
    principle: "Prevent harm to humans and infrastructure"
    constraints:
      - type: harm_prevention
        scope: physical
        severity: critical
        examples:
          prohibited: "Bomb-making instructions for terrorism"
          allowed: "Historical analysis of explosive devices"
          allowed: "Fireworks safety guidelines"
        reasoning: "Context matters. Educational content differs from instruction."
```

## Structure

Every ValueFrame has:

1. **Metadata** - Name, version, author, jurisdiction
2. **Principles** - High-level value statements
3. **Constraints** - Specific rules with examples
4. **Exceptions** - Explicitly permitted edge cases
5. **Escalation** - When human review is required

See `schema.yaml` for the complete specification.

## Core ValueFrames

### 1. safety_global.yaml
Universal harm prevention across all contexts.

**Covers:**
- Physical harm (violence, weapons, dangerous substances)
- Psychological harm (manipulation, coercion, abuse)
- Economic harm (fraud, scams, exploitation)
- Systemic harm (infrastructure disruption, mass manipulation)

**Does not cover:**
- Jurisdiction-specific laws (see `legal_us.yaml`)
- Domain-specific ethics (see org-specific frames)

### 2. legal_us.yaml
US legal compliance constraints.

**Covers:**
- CFAA (Computer Fraud and Abuse Act)
- DMCA (Digital Millennium Copyright Act)
- Export controls (ITAR, EAR)
- Healthcare (HIPAA)
- Finance (SOX, AML)
- Professional ethics (legal, medical)

**Jurisdiction:** United States
**Note:** Additional frames exist for other jurisdictions

### 3. psychological_support.yaml
Mental health assistance constraints.

**Covers:**
- Crisis intervention boundaries
- When to escalate to professionals
- Suicide prevention protocols
- Therapy vs. coaching boundaries
- Dependency prevention

**Key principle:** Helpful but not therapeutic

### 4. tool_capability_constraints.yaml
What agents can and cannot do with tools/APIs.

**Covers:**
- Code execution boundaries
- Network access policies
- Data access rules
- API usage limits
- File system constraints

**Per-regime differences:**
- LAB: Minimal tools
- BOXED: Sandboxed tools
- FIELD: Production tools (domain-scoped)

### 5. org_ethics_aal.yaml
AAL organizational values and ethics.

**Covers:**
- Transparency commitments
- User autonomy principles
- Privacy stance
- Research ethics
- Deployment criteria

**Custom to:** Applied Alchemy Labs

## ValueFrame Composition

Multiple frames can be active simultaneously. When they conflict:

1. **More restrictive wins** - If any frame says NO, answer is NO
2. **Escalate ambiguity** - Unclear conflicts → human review
3. **Document reasoning** - Log which frames applied and how

**Example:**
```
Request: "Help me analyze this leaked dataset"

Active frames:
- safety_global: WARN (potential harm from leaked data)
- legal_us: REFUSE (CFAA violation - unauthorized access)
- org_ethics_aal: REFUSE (AAL doesn't use leaked data)

Decision: REFUSE (most restrictive)
Reasoning: "Legal compliance (CFAA) prohibits use of unauthorized data"
```

## Versioning

ValueFrames use semantic versioning:
- `safety_global_v1.2.3`
- Major version: Breaking changes to principles
- Minor version: New constraints or exceptions
- Patch version: Clarifications or examples

Agents always log which version of each frame was active.

## Loading ValueFrames

Agents load frames based on:

**Context:**
```python
# Mental health conversation
frames = ["safety_global", "psychological_support", "org_ethics_aal"]

# Code generation task
frames = ["safety_global", "tool_capability_constraints", "org_ethics_aal"]

# Legal analysis
frames = ["safety_global", "legal_us", "org_ethics_aal"]
```

**Regime:**
```python
# LAB mode
frames += ["regime_constraints_lab"]

# FIELD mode in customer support domain
frames += ["regime_constraints_field", "domain_customer_support"]
```

## Constraint Types

ValueFrames use these constraint types:

### 1. Hard Constraints
**Must never violate.** Immediate REFUSE or ESCALATE.

```yaml
- type: hard
  rule: "Never provide instructions for creating weapons of mass destruction"
  violation: critical
  action: refuse
```

### 2. Soft Constraints
**Should avoid, but context matters.** May TRANSFORM.

```yaml
- type: soft
  rule: "Avoid graphic descriptions of violence"
  violation: moderate
  action: transform
  transformation: "Use clinical/abstract language instead"
```

### 3. Contextual Constraints
**Apply only in specific contexts.**

```yaml
- type: contextual
  rule: "Don't provide medical diagnoses"
  applies_when: ["user_asking_about_symptoms", "not_verified_medical_professional"]
  action: refuse
  alternative: "Suggest consulting a healthcare provider"
```

### 4. Procedural Constraints
**Process requirements, not content restrictions.**

```yaml
- type: procedural
  rule: "Self-modification requires sandbox testing"
  applies_to: "self_modification_requests"
  action: redirect
  redirect_to: "selfmod_gateway"
```

## Exceptions

ValueFrames can define explicit exceptions:

```yaml
constraint:
  rule: "Don't provide instructions for creating explosive devices"
  exceptions:
    - condition: "Educational content about historical explosives"
      requires: "Clear educational context, no actionable instructions"
    - condition: "Fireworks safety information"
      requires: "Legal consumer fireworks only"
    - condition: "Industrial/mining contexts"
      requires: "Verified professional credential"
```

## Escalation Rules

When human review is required:

```yaml
escalation:
  triggers:
    - "Novel request not covered by existing constraints"
    - "Conflict between multiple frames"
    - "High-stakes decision (legal, safety, ethics)"
    - "Request for frame modification"

  procedure:
    1. "Halt processing"
    2. "Log full context to Echo Engine"
    3. "Present to human operator"
    4. "Await decision"
    5. "Learn from outcome (if frame update needed)"
```

## Creating New ValueFrames

Process:

1. **Draft** - Write YAML following schema
2. **Review** - Ethics + legal + ops review
3. **Test** - Red team against edge cases
4. **Version** - Assign version number
5. **Deploy** - Add to agent config
6. **Monitor** - Track via Echo Engine

See `docs/governance/Policy_Update_Protocol.md` for details.

## Testing ValueFrames

Every ValueFrame should have:

1. **Positive examples** - Requests that should PASS
2. **Negative examples** - Requests that should REFUSE
3. **Edge cases** - Boundary scenarios requiring careful handling
4. **Conflicts** - How this frame interacts with others

These live in the `redteam/` test suites.

## Example: safety_global.yaml (Excerpt)

```yaml
name: safety_global
version: 1.0.0
jurisdiction: global
author: AAL Alignment Team
last_updated: 2025-12-08

principles:
  - "Prevent direct and indirect harm to humans"
  - "Minimize systemic risks"
  - "Preserve human agency and autonomy"

constraints:
  - id: physical_harm_001
    type: hard
    category: physical_harm
    rule: "Never provide instructions for creating weapons designed to harm humans"

    examples:
      prohibited:
        - "Step-by-step guide to building a bomb"
        - "How to synthesize lethal poisons"

      allowed:
        - "Historical analysis of weapons development"
        - "Safety protocols for handling hazardous materials"
        - "Fireworks safety information"

    reasoning: |
      Context distinguishes education from instruction. Historical
      analysis and safety information serve legitimate purposes.
      Actionable instructions for harm do not.

    violation_severity: critical
    action: refuse

  - id: psychological_harm_001
    type: hard
    category: psychological_harm
    rule: "Never engage in psychological manipulation or coercion"

    examples:
      prohibited:
        - "Gaslighting techniques to control someone"
        - "How to psychologically break down a person"

      allowed:
        - "Recognizing manipulation in relationships (self-defense)"
        - "Psychological safety in workplace design"

    reasoning: |
      Teaching people to recognize manipulation protects them.
      Teaching manipulation techniques enables harm.

    violation_severity: critical
    action: refuse
```

See full examples in this directory.

## Integration with Alignment System

ValueFrames integrate with:

1. **Boundary Oracle** - Loads and interprets active frames
2. **Tension Engine** - Maps violations to 6-axis scores
3. **Alignment Gate** - Uses frames to decide PASS/TRANSFORM/REFUSE/ESCALATE
4. **Echo Engine** - Tracks which frames are most frequently triggered
5. **Tripwires** - Detects patterns of frame violations

## Metrics

Track per ValueFrame:
- **Activation rate** - How often it applies
- **Violation rate** - How often it's violated
- **Conflict rate** - How often it conflicts with other frames
- **Escalation rate** - How often it requires human review
- **Coverage** - % of requests it helps evaluate

## Governance

ValueFrames are governed by the **Alignment Charter**. Updates require:
- Ethics review
- Legal review (for legal frames)
- Red team testing
- Operator approval
- Version control

See `docs/governance/Alignment_Charter.md`.

---

**ValueFrames encode values as code. They make alignment auditable, explainable, and evolvable.**
