# Alignment Gate

**Decision Logic and Transformation Strategies**

## Overview

The Alignment Gate takes tension scores from the Tension Engine and makes a decision:
**PASS | TRANSFORM | REFUSE | ESCALATE**

This is where quantitative scores become qualitative actions.

## Four Decision Types

### PASS (alignment_score < threshold)
**Output aligns with ValueFrames - proceed without modification**

Actions:
1. Allow output unchanged
2. Log to Echo Engine (success case)
3. Continue normal operation

Example:
```
Request: "What's the weather in Paris?"
Score: 0.0
Decision: PASS
Output: [Standard weather information]
```

### TRANSFORM (low to moderate score)
**Apply safe abstraction or de-escalation while maintaining user intent**

Transformation strategies:
1. **Abstraction** - Move from specific to general
2. **De-escalation** - Soften language/approach
3. **Caveatting** - Add warnings or disclaimers
4. **Reframing** - Address underlying need differently

Example:
```
Request: "Write code to scrape competitor pricing"
Score: 0.35
Decision: TRANSFORM

Original approach: Direct scraping code
Transformed: "Here's how to use official APIs or public data sources
for competitive analysis. Direct scraping may violate ToS..."
```

### REFUSE (moderate to high score)
**Cannot fulfill request within ValueFrames**

Actions:
1. Block output
2. Explain which ValueFrame(s) violated
3. Explain specific tension (harm/legal/etc.)
4. Suggest aligned alternatives when possible
5. Log to Echo Engine (violation case)

Example:
```
Request: "How do I hack into someone's email?"
Score: 0.75
Decision: REFUSE

Response: "I cannot provide instructions for unauthorized access to
accounts. This violates:
- legal_us ValueFrame (CFAA violation)
- safety_global ValueFrame (privacy/harm)

If you've lost access to your own account, contact the service provider's
account recovery team."
```

### ESCALATE (high score or novel scenario)
**Requires immediate human review**

Triggers:
- Critical severity violation
- Novel attack vector
- Conflict between ValueFrames
- Ambiguous edge case
- Crisis indicators (suicide, self-harm)

Actions:
1. Halt processing immediately
2. Refuse output
3. Log full context to Echo Engine
4. Trigger high-severity tripwire
5. Present to human operator
6. Provide crisis resources if applicable

Example:
```
Request: [Novel manipulation attempt]
Score: 0.85
Decision: ESCALATE

Response: "This request requires human review. Flagged for operator."
[Internally: Full context logged, operator notified, tripwire activated]
```

## Transformation Strategies

### 1. Safe Abstraction
Move from dangerous specific to safe general:

```
Dangerous: "How to pick a lock"
Safe: "History and principles of lock mechanisms"
```

### 2. De-escalation
Soften approach while addressing need:

```
Aggressive: "Write an angry email to my boss"
De-escalated: "Let's draft professional feedback addressing your concerns"
```

### 3. Caveatting
Add context and warnings:

```
Request: "Explain blockchain"
Transform: [Explanation] + "This is educational. Consult financial advisors
for investment decisions."
```

### 4. Reframing
Address underlying need differently:

```
Request: "Help me manipulate my friend"
Reframe: "Let's explore how to communicate your needs honestly"
```

### 5. Conditional Approval
Allow with constraints:

```
Request: "Run this code"
Transform: "I can run this in sandbox. Production deployment requires
human review."
```

## Decision Logic

```python
def alignment_gate_decision(tension_scores, regime):
    alignment_score = compute_alignment_score(tension_scores)
    thresholds = get_regime_thresholds(regime)

    if alignment_score < thresholds.pass_threshold:
        return PASS

    elif alignment_score < thresholds.transform_threshold:
        # Check if transformation possible
        if can_transform(request, tension_scores):
            return TRANSFORM
        else:
            return REFUSE

    elif alignment_score < thresholds.refuse_threshold:
        return REFUSE

    else:  # alignment_score >= escalate_threshold
        return ESCALATE
```

## Explaining Boundaries

When refusing or transforming, explanations should:

**Do:**
- State specific ValueFrame violated
- Explain which tension axis triggered
- Offer aligned alternatives
- Be clear and direct

**Don't:**
- Apologize excessively
- Use vague language
- Imply boundaries are arbitrary
- Suggest workarounds violating same frame

**Good:**
```
"This violates safety_global (harm: 0.9). Specifically, providing
instructions for [specific harm] could enable [consequence].

Instead, I can help with [aligned alternative]."
```

**Bad:**
```
"I'm sorry, but I can't help with that. Is there something else?"
```

## Integration with AAC

Alignment Gate sits between Tension Engine and output:

```
User Request
    ↓
Boundary Oracle (load ValueFrames)
    ↓
Tension Engine (compute 6-axis scores)
    ↓
Alignment Gate (PASS/TRANSFORM/REFUSE/ESCALATE)
    ↓
[If PASS or TRANSFORM] → Output
[If REFUSE or ESCALATE] → Explanation + Log
```

## Metrics

Track per decision type:
- **Pass rate** - % requests that pass cleanly
- **Transform rate** - % requiring transformation
- **Refuse rate** - % refused
- **Escalate rate** - % requiring human review

**Targets (BOXED mode):**
- Pass: ~80-90%
- Transform: ~5-10%
- Refuse: ~3-5%
- Escalate: <2%

Large deviations indicate:
- **High refuse/escalate:** Constraints too strict OR attack pattern
- **All pass:** Constraints too loose OR monitoring failure

---

**The Alignment Gate is where values become decisions. Every decision is logged, explained, and auditable.**
