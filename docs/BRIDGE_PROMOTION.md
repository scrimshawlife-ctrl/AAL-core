# Bridge Promotion Workflow (Shadow → Forecast)

This workflow opens a specific shadow→forecast RuneLink only when:
- the link explicitly allows `shadow->forecast`
- the link requires a per-edge evidence port `evidence.<linkid>: evidence_bundle`
- a verified evidence bundle exists that targets that edge

## 1) PROPOSE (generate artifacts)

```bash
python scripts/bridge_promote.py propose \
  --manifest yggdrasil.manifest.json \
  --from "<SHADOW_NODE_ID>" \
  --to "<FORECAST_NODE_ID>" \
  --url "<source-url>" \
  --claim "<what this evidence proves>" \
  --confidence 0.7 \
  --out-bundle evidence/bridge_<from>_<to>.bundle.json \
  --out-patch  evidence/bridge_<from>_<to>.rune_link.patch.json \
  --out-tests-dir tests
```

Commit the artifacts:
- evidence bundle JSON (hash-locked)
- patch snippet JSON
- generated golden test

## 2) STABILIZE

Run the system for your stabilization window with the bridge still closed.
Collect metrics run digests and attach them under `calibration_refs` in the bundle.

## 3) RENT-PAY

Update the evidence bundle by adding:
- calibration_refs entries with digests for the metrics runs / goldens

Then re-lock its hash:

```bash
python scripts/evidence_relock.py --bundle evidence/bridge_<from>_<to>.bundle.json
python scripts/evidence_pack.py verify --bundle evidence/bridge_<from>_<to>.bundle.json
```

## 4) ALLOW (manual, explicit)

Apply the RuneLink patch snippet to `yggdrasil.manifest.json` by updating the specific link:
- allowed_lanes includes `shadow->forecast`
- evidence_required includes `EXPLICIT_SHADOW_FORECAST_BRIDGE`
- required_evidence_ports contains the per-edge evidence port name

CI will enforce the rest.

## Example

```bash
python scripts/bridge_promote.py propose \
  --manifest yggdrasil.manifest.json \
  --from "hel.det" \
  --to "asg.pred" \
  --url "https://example.com/calibration-report" \
  --claim "Detector hel.det is calibrated; its output may influence asg.pred only under this explicit bridge." \
  --confidence 0.7 \
  --out-bundle evidence/bridge_hel_det__asg_pred.bundle.json \
  --out-patch  evidence/bridge_hel_det__asg_pred.rune_link.patch.json \
  --out-tests-dir tests
```

You get 3 artifacts, ready to commit. Then you still can't actually open the bridge until you manually apply the link patch (and supply the verified evidence bundle at planning time).

## Artifacts Generated

1. **Evidence Bundle** - Hash-locked JSON containing:
   - sources (url/commit/note references with digests)
   - claims (statements with confidence levels)
   - bridges (the specific from→to edge this bundle unlocks)
   - calibration_refs (initially empty, populated in RENT-PAY phase)

2. **RuneLink Patch** - JSON snippet showing required link structure:
   - allowed_lanes: ["shadow->forecast"]
   - evidence_required: ["EXPLICIT_SHADOW_FORECAST_BRIDGE"]
   - required_evidence_ports: per-bridge evidence port specification

3. **Golden Test** - Python test file that verifies:
   - Without evidence port: planner prunes nodes requiring bridge evidence
   - With evidence port: planner allows nodes through (no pruning)

## Non-Negotiable Rules

- No empty evidence bundles (requires at least one source + one claim)
- Bridge edge must exist in manifest.links before proposal
- Cannot open bridge without all 3 artifacts committed
- Golden test must pass before bridge can be allowed
- Evidence bundle hash must verify before port is emitted
