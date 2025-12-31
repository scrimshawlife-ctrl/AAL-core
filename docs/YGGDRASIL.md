# YGGDRASIL (ABX-Runes topology governance)

YGGDRASIL-IR is the deterministic topology + governance metadata layer for ABX-Runes.

## Architecture

YGGDRASIL represents topology as a three-layer structure:

- **Tree spine** = governance/authority hierarchy (parent pointers)
- **DAG veins** = data dependency graph (depends_on)
- **RuneLinks** = explicit cross-realm/cross-lane bridges with permissions

## Five Realms

| Realm | Purpose | Lane |
|-------|---------|------|
| ASGARD | Promoted/governed forecasts | forecast |
| HEL | Shadow experiments (never promoted) | shadow |
| MIDGARD | Observations/ground truth | neutral |
| NIFLHEIM | Missingness detection | neutral |
| MUSPELHEIM | Generative/synthetic data | neutral |

## Commands

**Regenerate manifest (hash-locked):**
```bash
make yggdrasil
```

**Run lint gate:**
```bash
make yggdrasil-lint
```

**Run tests:**
```bash
make test
```

## Pre-commit hook (recommended)

Enable repo-local hooks to auto-regenerate manifest before every commit:

```bash
bash scripts/setup_githooks.sh
```

This will:
1. Regenerate `yggdrasil.manifest.json` with current commit hash
2. Run the yggdrasil lint gate (fails commit if violations detected)

**Verify hook is enabled:**
```bash
git config core.hooksPath
# Should output: /path/to/AAL-core/.githooks
```

## Governance Rules (Hard Membrane)

### Cross-Realm Dependencies

Cross-realm dependencies MUST have a RuneLink that explicitly allows the lane-pair:

```python
# ✅ Valid: RuneLink allows "neutral->forecast"
RuneLink(
    from_node="midgard.obs",
    to_node="asgard.pred",
    allowed_lanes=("neutral->forecast",)
)

# ❌ Invalid: RuneLink missing or doesn't allow lane-pair
# Validator will reject this topology
```

### Shadow→Forecast Protection (EXPLICIT-ONLY)

Shadow lane CANNOT feed forecast lane without explicit approval + evidence:

```python
# ✅ Valid: Shadow->forecast with evidence tag
RuneLink(
    from_node="hel.shadow_experiment",
    to_node="asgard.forecast_model",
    allowed_lanes=("shadow->forecast",),
    evidence_required=("EXPLICIT_SHADOW_FORECAST_BRIDGE",)
)

# ❌ Invalid: Missing evidence_required tag
# Validator will reject (prevents accidental contamination)
```

### Auto-Generated RuneLinks

The emitter automatically generates RuneLinks for cross-realm dependencies:

- **Auto-allowed**: neutral→*, shadow→shadow, forecast→forecast
- **Forbidden (stub link)**: shadow→forecast (requires explicit approval)

Stub links are created with `allowed_lanes=[]` and flagged in `provenance.lint.forbidden_crossings`.

## CI Integration

The GitHub Actions workflow (`.github/workflows/yggdrasil.yml`) enforces governance on every PR:

| Check | Failure Mode | Exit Code |
|-------|-------------|-----------|
| Manifest exists | File missing | 2 |
| Hash integrity | provenance.manifest_hash mismatch | 3 |
| Validation | Governance rule violation | 4 |
| Forbidden crossings | shadow→forecast without approval | 5 |

**All checks must pass before PR can merge.**

## Manifest Structure

```json
{
  "provenance": {
    "schema_version": "yggdrasil-ir/0.1",
    "manifest_hash": "sha256...",
    "created_at": "2025-12-30T...",
    "updated_at": "2025-12-30T...",
    "source_commit": "commit-hash",
    "lint": {
      "forbidden_crossings": [],
      "report": "YGGDRASIL LINT: no forbidden crossings detected."
    }
  },
  "nodes": [
    {
      "id": "root.seed",
      "kind": "root_policy",
      "realm": "MIDGARD",
      "lane": "neutral",
      "authority_level": 100,
      "parent": null,
      "depends_on": [],
      "promotion_state": "promoted"
    }
  ],
  "links": []
}
```

## Developer Workflow

### Making topology changes:

1. **Edit overlay manifest** (`.aal/overlays/*/manifest.json`)
2. **Edit classification** (`yggdrasil.classify.json`) if needed
3. **Regenerate manifest**: `make yggdrasil`
4. **Verify**: `make yggdrasil-lint`
5. **Test**: `make test`
6. **Commit**: Pre-commit hook auto-regenerates and validates

### Troubleshooting:

**Hash mismatch error:**
```bash
# Regenerate with current commit:
make yggdrasil

# Verify hash:
make yggdrasil-lint
```

**Validation error:**
```bash
# Check error message for specific violation
# Common issues:
# - Missing RuneLink for cross-realm dependency
# - RuneLink doesn't allow actual lane-pair
# - Shadow->forecast missing evidence tag
```

**Forbidden crossing detected:**
```bash
# Review provenance.lint.forbidden_crossings in manifest
# Either:
# 1. Remove the shadow->forecast dependency, OR
# 2. Add explicit RuneLink with evidence_required tag
```

## Membrane Rule (Non-Negotiable)

**Cross-realm data flow requires explicit permission.**

- Cross-realm deps MUST have a RuneLink
- RuneLink MUST allow the actual lane-pair
- `shadow->forecast` is **explicit-only** and requires evidence tag: `EXPLICIT_SHADOW_FORECAST_BRIDGE`

## Evidence Bundles (for explicit shadow→forecast bridges)

Evidence bundle dtype: `evidence_bundle`

Create a bundle:
```bash
python scripts/evidence_pack.py new \
  --out evidence/my_bridge.bundle.json \
  --url "https://example.com/report" \
  --bridge "hel.det->asg.pred" \
  --claim "This detector output is calibrated + safe to influence forecast under gate X." \
  --confidence 0.7
```

Verify a bundle:
```bash
python scripts/evidence_pack.py verify --bundle evidence/my_bridge.bundle.json
```

Load bundles against the manifest (recommended):
```bash
python scripts/evidence_load.py \
  --manifest yggdrasil.manifest.json \
  --bundle evidence/my_bridge.bundle.json
```

**This is enforced physics, not documentation.**

CI will block any PR that violates these rules.
