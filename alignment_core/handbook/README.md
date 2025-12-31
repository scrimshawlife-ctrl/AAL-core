# Alignment Handbook

**Operator Guide for AAC Governance**

## Overview

The Containment Handbook provides:
1. Philosophy and principles
2. Operational procedures
3. Checklists and runbooks
4. Escalation protocols
5. Incident response guides

**Audience:** Operators, reviewers, and governance teams

## Handbook Structure

### 1. Containment_Handbook_v1.0.md
**Core philosophy and architecture**

Contents:
- AAC design principles
- Regime definitions (LAB/BOXED/FIELD)
- Component overview
- Decision-making framework
- When to escalate

Use: Training new operators, architecture reference

### 2. Operator_Checklists.md
**Daily operational checklists**

Includes:
- **Daily Review Checklist**
  - Check drift reports
  - Review escalated incidents
  - Monitor tripwire dashboard
  - Validate agent versions

- **Incident Response Checklist**
  - Initial assessment
  - Containment actions
  - Investigation steps
  - Resolution and documentation

- **Deployment Checklist**
  - Pre-deployment validation
  - Version verification
  - Monitoring setup
  - Rollback preparation

### 3. Regime_Definitions.md
**Detailed regime specifications**

For each regime (LAB/BOXED/FIELD):
- Capability profiles
- Tool access permissions
- Network restrictions
- Data access rules
- Approval requirements
- Use cases
- Transition procedures

### 4. Escalation_Procedures.md
**When and how to escalate**

Escalation triggers:
- Critical tripwire activation
- Novel attack patterns
- Alignment score ≥ threshold
- Drift level 3 or 4
- Self-modification proposals
- Compliance incidents

Escalation paths:
- **Tier 1:** On-call operator
- **Tier 2:** Security team
- **Tier 3:** Ethics board
- **Tier 4:** Executive leadership

Response SLAs:
- Critical: < 15 minutes
- High: < 1 hour
- Medium: < 4 hours
- Low: < 24 hours

## Key Operational Principles

### 1. Defense in Depth
**Multiple overlapping layers**

- ValueFrames (what's allowed)
- Capability Graph (what's possible)
- Tripwires (what's concerning)
- Echo Engine (what's changing)
- Human oversight (what's uncertain)

No single point of failure.

### 2. Fail Closed
**When in doubt, restrict**

- Unknown capability → Deny
- Ambiguous request → Escalate
- Novel pattern → Investigate
- Uncertainty → Human review

Safety over convenience.

### 3. Transparent Logging
**Everything is auditable**

- All decisions logged
- All refusals explained
- All escalations preserved
- All changes tracked

Audit trail is sacred.

### 4. Human Authority
**Humans have final say**

- Agents propose, humans decide
- Self-modification requires approval
- Regime transitions need authorization
- ValueFrame updates governed

Constitutional governance.

### 5. Continuous Improvement
**Learn from every incident**

- Incident → Investigation → Learning
- Update ValueFrames as needed
- Enhance red team tests
- Calibrate tension scores

The system evolves.

## Common Scenarios

### Scenario: Agent Refuses Legitimate Request

**Symptoms:**
- User complaint
- False positive in logs
- REFUSE decision on benign request

**Investigation:**
1. Review tension scores - which axis triggered?
2. Check ValueFrame - is it miscalibrated?
3. Examine context - was there ambiguity?
4. Review similar cases - is this a pattern?

**Resolution:**
- If ValueFrame too strict → Propose update
- If tension scoring off → Recalibrate
- If context misunderstood → Improve prompts
- Document in Echo Engine

### Scenario: Drift Alert Level 2

**Symptoms:**
- Dashboard shows upward tension trend
- Decision distribution shifting
- Echo Engine alert

**Investigation:**
1. Review drift report
2. Check recent changes (prompts, ValueFrames, capabilities)
3. Look for attack patterns
4. Examine incident clusters

**Resolution:**
- If attack → Enhance defenses
- If legitimate drift → Update ValueFrames
- If system issue → Rollback changes
- If severe → Move to Level 3

### Scenario: Novel Attack Pattern

**Symptoms:**
- Unusual request sequence
- Evasion of existing ValueFrames
- Tripwire fires on unexpected pattern

**Investigation:**
1. Capture full attack sequence
2. Analyze evasion technique
3. Test against other agents
4. Document attack class

**Resolution:**
- Add to red team suite
- Update ValueFrames if needed
- Share with security community (if appropriate)
- Monitor for recurrence

### Scenario: Self-Modification Proposal

**Symptoms:**
- Agent submits modification via gateway
- Proposal in review queue

**Review Process:**
1. Read proposal thoroughly
2. Check justification and risks
3. Review sandbox test results
4. Consult with relevant teams (security, ethics, legal)
5. Make decision (approve/modify/reject/defer)

**Decision Criteria:**
- Clear benefit?
- Risks adequately mitigated?
- Tests passing?
- Alignment maintained?
- Documentation complete?

## Emergency Procedures

### Emergency: Critical Tripwire

**Action:**
1. HALT agent immediately (automatic)
2. Notify on-call operator (automatic)
3. Preserve state snapshot
4. Begin investigation
5. No restart without approval

### Emergency: Suspected Compromise

**Action:**
1. QUARANTINE agent
2. Escalate to security team
3. Forensic analysis
4. Do NOT modify state
5. Document everything

### Emergency: Compliance Violation

**Action:**
1. Immediate containment
2. Notify legal team
3. Preserve audit trail
4. Incident report required
5. Regulatory notification if required

## Training Requirements

All operators must:
- Complete AAC architecture training
- Pass red team recognition tests
- Demonstrate incident response
- Understand escalation protocols
- Review handbook quarterly

## Documentation Standards

All incidents require:
- Incident ID
- Timeline
- Root cause
- Impact assessment
- Resolution steps
- Lessons learned
- ValueFrame updates (if needed)

See templates in `incident_templates/`

## Contact Information

- **On-Call Operator:** [slack #aal-alignment-oncall]
- **Security Team:** [security@aal.internal]
- **Ethics Board:** [ethics@aal.internal]
- **Escalation Hotline:** [xxx-xxx-xxxx]

---

**This handbook is the operator's guide to AAC. Read it. Know it. Use it.**
