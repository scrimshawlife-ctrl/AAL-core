# Portfolio Optimizer v0.4 (ABX-Runes + ERS)

## Contract
Select a set of tuning actions across modules under shared budgets, deterministically.
Emit `PortfolioTuningIR` + per-module `TuningIR`s. ERS applies atomically at cycle boundary.

## Inputs
- Registry snapshot (module_id -> tuning_envelope, metrics_envelope, capability)
- Metrics snapshot (module_id -> MetricsEnvelope-like dict)
- Portfolio policy (weights + budgets + max_changes_per_cycle)
- Stabilization state (cycles since change per (module, knob))

## Selection Algorithm (v0.4)
Deterministic greedy knapsack-lite:
1) Enumerate candidates (module, knob, proposed_value) from envelopes and policy.
2) Filter by:
   - capability required
   - hot_apply
   - stabilization eligibility
3) Score candidates using weighted objective.
4) Pick in stable order until budgets / max_changes reached.

## Outputs
- PortfolioTuningIR:
  - schema_version
  - portfolio_hash
  - source_cycle_id
  - policy (weights/budgets)
  - items: list of embedded TuningIR dicts
  - notes: deterministic explainability fields

## Notes
- v0.4 focuses on `applied_tune` decisions. Promotion remains v0.2 via evidence + rent-payment.
- No envelope => no candidates. No capability => knob excluded.
- Atomic apply: ERS validates all items first, then applies eligible subset.

