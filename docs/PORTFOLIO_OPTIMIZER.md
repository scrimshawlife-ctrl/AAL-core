# Portfolio Optimizer v0.4 (ABX-Runes + ERS)

## v0.5 Upgrade
Replace heuristic impacts with measured deltas. Add significance/noise gates.
Portfolio selection uses effect sizes learned from observed before/after metrics.

## Contract
Select a set of tuning actions across modules under shared budgets, deterministically.
Emit `PortfolioTuningIR` + per-module `TuningIR`s. ERS applies atomically at cycle boundary.

## Selection Algorithm (v0.5)
- Candidate impacts come from `EffectStore` (measured deltas).
- Candidates must pass `SignificanceGate` (min_samples + min_effect thresholds).
- Optional policy: allow unknown effects as shadow-only suggestions (not applied).

## Persistence
EffectStore is persisted under `.aal/effects_store.json` (canonical + hashed).
This enables restart-safe learning of knob impacts.

