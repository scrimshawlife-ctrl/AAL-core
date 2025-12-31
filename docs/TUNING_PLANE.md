# Universal Tuning Plane v0.1 (ABX-Runes + ERS)

## Contract
ABX-Runes may hot-tune any module through ERS using typed, bounded tuning knobs.
All tuning is capability-gated and stabilization-governed.

This is governance + optimization plumbing, not domain logic.

## Components
- ABX-Runes:
  - `abx_runes/tuning/*` (schemas, IR, validators)
- ERS (AAL-core):
  - `aal_core/ers/tuning_apply.py` (hot apply at cycle boundary)
  - `aal_core/ers/capabilities.py` (cap tokens / allowlist)
  - `aal_core/ers/stabilization.py` (stabilization window gate)

## Key Artifacts
### TuningEnvelope
Declares allowable knobs for a module (typed + bounds):
- knob kind: `int|float|bool|enum|duration_ms`
- bounds: min/max or enum set
- hot_apply: boolean
- stabilization_cycles: int
- capability_required: string

### MetricsEnvelope
Normalizes optimization feedback:
- latency p50/p95
- cost_units
- throughput
- error_rate
- optional drift_score / entropy_proxy

### TuningIR
ABX emits:
- target: node_id/module_id
- knob assignments (must validate against envelope)
- mode: `shadow_tune | applied_tune | promoted_tune`
- provenance: `ir_hash`, `source_cycle_id`, `reason_tags`

## Execution Boundary
ABX emits `TuningIR`.
ERS applies it at cycle boundaries only if:
1) capability allows knob
2) knob is declared + bounded
3) stabilization gate allows (unless mode is shadow_tune -> "dry-run only")

## Determinism
All JSON artifacts are canonicalized (sorted keys, stable separators).
IR includes a content hash computed with the provenance field blanked.
