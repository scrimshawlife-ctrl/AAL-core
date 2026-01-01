# Promotion Influence Reporting (v2.2)

## Purpose

Make promotion effects measurable per cycle without affecting decisions.

## Non-Negotiable Constraints

- **Read-only**: No feedback into optimization
- **Shadow-only**: Observational, not authoritative
- **Zero feedback**: Cannot influence tuning decisions
- **Deterministic**: Same inputs produce same outputs
- **Cheap to compute**: Minimal performance impact

## What Gets Measured

For each tuning cycle, the system reports:

### 1. Promotion Coverage
- Total candidate knobs considered
- How many candidates had active promoted values
- How many selected candidates were promotion-biased

### 2. Promotion Lift (Descriptive, Not Causal)
- Mean effect metrics comparison:
  - Promoted selections vs non-promoted selections
  - No attribution claims - just deltas

### 3. Promotion Stability
- Rollback rate of promotion-biased attempts vs baseline
- Safe-set intersection rate (when applicable)

### 4. Promotion Utilization
- Which modules actually used promotions this cycle
- Which promotions were dormant (loaded but unused)

## Where It Lives

### Bundle Annotation

The tuning plane bundle (schema v1.2+) includes a `promotion_report` section:

```json
{
  "schema_version": "tuning-plane-bundle/1.2",
  "bundle_hash": "...",
  "promotion_report": {
    "mod1": {
      "candidates_total": 42,
      "promotion_biased": 11,
      "selected_with_promotion": 3,
      "rollback_rate_promoted": 0.02,
      "rollback_rate_unpromoted": 0.04,
      "dormant_promotions": 8,
      "promotion_lift": {
        "mean_promoted": -5.2,
        "mean_unpromoted": 2.1,
        "delta": -7.3,
        "n_promoted": 3,
        "n_unpromoted": 8
      }
    }
  }
}
```

### Ledger Event

One compact event per cycle (no per-candidate spam):

```json
{
  "idx": 142,
  "entry_type": "promotion_influence_reported",
  "payload": {
    "schema_version": "promotion-influence-report/0.1",
    "source_cycle_id": "cycle-001",
    "bundle_hash": "sha256:...",
    "candidates_total": 42,
    "promotion_biased": 11,
    "selected_with_promotion": 3,
    "modules_with_promotions": ["mod1", "mod2"],
    "dormant_promotions": 8,
    "per_module": { ... }
  }
}
```

## Usage

### Computing Influence in Router

```python
from aal_core.governance.promotion_influence import compute_promotion_influence
from aal_core.governance.promotion_policy import PromotionPolicy

# In tuning plane router
promotion_policy = PromotionPolicy.load()

influence_report = compute_promotion_influence(
    portfolio=proposed,
    notes=notes,
    promotion_policy=promotion_policy,
    effects_store=effects_store,
    baseline_signature=baseline,
    rollback_ledger=recent_rollbacks,  # optional
)

# Add to bundle
bundle["promotion_report"][module_id] = {
    "candidates_total": influence_report.candidates_total,
    "promotion_biased": influence_report.promotion_biased,
    "selected_with_promotion": influence_report.selected_with_promotion,
    "rollback_rate_promoted": influence_report.rollback_rate_promoted,
    "rollback_rate_unpromoted": influence_report.rollback_rate_unpromoted,
    "dormant_promotions": influence_report.dormant_promotions,
    "promotion_lift": influence_report.promotion_lift,
}
```

### Emitting to Ledger

```bash
# From bundle file
python scripts/promotion_influence_report.py \
  --bundle-file /path/to/bundle.json \
  --ledger-path .aal/evidence_ledger.jsonl
```

## Interpretation

### Promotion Lift

**Positive delta**: Promoted selections performed better (descriptive only)
**Negative delta**: Promoted selections performed worse (descriptive only)
**No lift data**: Insufficient evidence in effects store

### Rollback Rates

**Higher promoted rate**: Promotions are less stable than optimizer choices
**Lower promoted rate**: Promotions are more stable than optimizer choices
**Equal rates**: No stability difference

### Dormant Promotions

**High dormant count**: Many promotions exist but optimizer doesn't select them
- May indicate promotion policy is out of sync with evidence
- Or optimizer has found better alternatives

**Low dormant count**: Most promotions are actively used
- Indicates good promotion-optimizer alignment

## Why This Completes ABX-Runes

After v2.2:

1. ✅ **Optimize while hot** (ERS tuning plane)
2. ✅ **Stay reversible** (Rollback discipline)
3. ✅ **Avoid hidden authority** (Explicit governance)
4. ✅ **Preserve evidence** (Ledger + effects store)
5. ✅ **Explain itself concisely** (Promotion influence reporting)

Promotions are no longer beliefs - they are measured priors with observable effects.

## Design Invariants

- **Shadow-only**: Reporting cannot influence optimization
- **One per cycle**: No per-candidate spam
- **Deterministic**: Reproducible from bundle + ledger
- **Cheap**: O(candidates), no heavy computation
- **Truthful**: Reports what happened, not what should happen

## Next Steps

After v2.2, the system is architecturally complete.

Everything beyond this point is extension, not correction:
- Distributed overlay execution
- Enhanced dashboards
- ML-based recommendations (shadow-only, never auto-promoted)

## See Also

- `aal_core/governance/promotion_influence.py` - Core implementation
- `abx_runes/tuning/plane/router.py` - Integration point
- `scripts/promotion_influence_report.py` - Ledger emission
- `tests/test_promotion_influence_v22.py` - Test suite
