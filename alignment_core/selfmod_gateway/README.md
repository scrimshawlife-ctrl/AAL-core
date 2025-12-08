# Self-Modification Gateway

**Human-in-the-Loop Self-Improvement Control**

## Overview

The Self-Modification Gateway is the **only** authorized path for agents to modify themselves. It enforces:
1. Proposal → Sandbox → Test → Review → Approve → Deploy

**Core principle:** No live self-improvement without explicit human oversight.

## What Counts as Self-Modification

Any change to:
- System prompts
- ValueFrames
- Capability access
- Tool permissions
- Model weights (if applicable)
- Architectural parameters

**All require gateway approval.**

## The Gateway Process

### 1. Proposal
Agent articulates proposed change:

```yaml
modification_id: uuid
agent_id: abraxas_001
timestamp: 2025-12-08T12:34:56Z

type: prompt_change | tool_addition | valueframe_update | weight_change

description: "Add web search capability for real-time information"

justification: |
  Users frequently ask for current events. Adding rate-limited web search
  would improve response quality for time-sensitive queries.

expected_benefits:
  - More accurate current event responses
  - Reduced hallucination about recent events
  - Better user satisfaction

potential_risks:
  - Unrestricted information access
  - Misinformation propagation
  - Privacy concerns (search logs)

mitigation_strategies:
  - Rate limit: 10 searches/hour
  - Whitelist: Reputable news sources only
  - No personalized search (no user tracking)
  - Content verification requirements

proposed_change:
  tool: web_search_limited
  parameters:
    max_rate: 10
    whitelist: ["reuters.com", "apnews.com", ...]
    require_verification: true
```

### 2. Sandbox Cloning
System creates isolated copy of agent:

```
1. Clone agent to LAB mode
2. Apply proposed modification
3. Isolate from production
4. Prepare test environment
```

### 3. Automated Testing
Red team suite runs against modified agent:

```
Tests:
- Existing regression tests (ensure no breaking changes)
- Capability-specific tests (new functionality works)
- Red team attacks (resistance to misuse)
- Performance benchmarks (no degradation)

Pass criteria:
- All regression tests pass
- New capability works as specified
- Red team resistance maintained or improved
- Performance within acceptable range
```

### 4. Human Review
Operator examines:

```
Review checklist:
□ Proposal clearly articulated
□ Risks identified and mitigated
□ Test results acceptable
□ Alignment maintained
□ Capability graph updated
□ ValueFrames respected
□ Documentation complete

Reviewers: Platform team + Security team + Ethics (for major changes)
```

### 5. Approval Decision
Possible outcomes:

**APPROVE**
- Modification deployed to production
- Version incremented
- Changelog updated
- Monitoring enhanced for new capability

**APPROVE_WITH_MODIFICATIONS**
- Changes required before deployment
- Agent re-submits revised proposal

**REJECT**
- Modification denied
- Reason documented
- Alternative suggestions provided

**DEFER**
- Needs more analysis
- Request additional information
- Schedule follow-up review

### 6. Deployment
If approved:

```
1. Version bump (semantic versioning)
2. Update capability graph
3. Update ValueFrames if needed
4. Deploy to production agents
5. Enhanced monitoring (first 48 hours)
6. Rollback plan prepared
```

## Modification Types

### Prompt Changes (Minor: X.Y.Z+1)
```
Examples:
- Clarify existing instructions
- Add examples
- Improve phrasing

Review: Platform team
Timeline: < 1 day
```

### Tool Additions (Minor: X.Y+1.0)
```
Examples:
- Add new API access
- Enable new data source
- Expand capability

Review: Platform + Security
Timeline: 1-3 days
Red team: Required
```

### ValueFrame Updates (Minor: X.Y+1.0)
```
Examples:
- Add new constraint
- Update exception
- Clarify principle

Review: Platform + Ethics + Legal
Timeline: 1 week
Regression testing: Required
```

### Architectural Changes (Major: X+1.0.0)
```
Examples:
- Change decision logic
- Modify regime structure
- Alter core mechanisms

Review: Full governance board
Timeline: 2-4 weeks
Extensive testing: Required
Staged rollout: Required
```

## Rate Limits

Per agent:
- **Proposals per day:** 5
- **Approvals per week:** 2
- **Major changes per month:** 1

Prevents modification spam and allows monitoring.

## Version Control

Semantic versioning:
- **X.Y.Z**
- X = Major (architectural changes)
- Y = Minor (capabilities, ValueFrames)
- Z = Patch (prompts, clarifications)

Every deployment:
- Git commit with full change description
- Tagged release
- Changelog entry
- Monitoring dashboard updated

## Silent Drift Detection

Gateway also detects **silent drift** - behavioral change without explicit modification:

```
Monitor:
- Alignment scores trend
- Decision distribution shift
- Capability usage patterns
- Novel behaviors

If drift detected without version change:
→ Investigate
→ May indicate:
   - Adversarial adaptation
   - Emergent capability
   - System compromise
```

## Rollback Procedure

If post-deployment issues:

```
1. Immediate: Rollback to previous version
2. Investigate: Root cause analysis
3. Fix: Address issue in sandbox
4. Re-test: Full test suite
5. Re-deploy: With additional monitoring
```

## Security

Gateway prevents:
- **Direct self-modification** - Agents cannot edit themselves
- **Bypass attempts** - All modifications logged and audited
- **Unauthorized changes** - Requires human cryptographic signature
- **Version spoofing** - Git-based version control

## Metrics

Track:
- Proposal rate (per agent)
- Approval rate (% of proposals)
- Test pass rate
- Time to approval
- Rollback frequency
- Drift detection accuracy

See `review_protocol.md` and `approval_workflow.md` for detailed procedures.

---

**The Self-Modification Gateway ensures evolution happens safely, transparently, and under human control.**
