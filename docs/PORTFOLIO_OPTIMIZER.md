# Portfolio Optimizer v0.4 (ABX-Runes + ERS)

## v0.5 Upgrade
Replace heuristic impacts with measured deltas. Add significance/noise gates.
Portfolio selection uses effect sizes learned from observed before/after metrics.

## v0.6 Upgrade
Track variance (online Welford). Enforce significance via z-like gate:
`|mean| / stderr >= z_threshold` with `n >= min_samples`.

## Contract
Select a set of tuning actions across modules under shared budgets, deterministically.
Emit per-module `TuningIR`s. ERS applies atomically at cycle boundary.

## Persistence
EffectStore is persisted under `.aal/effects_store.json` (canonical + hashed).
This enables restart-safe learning of knob impacts.

## Noise Model
EffectStore stores `{n, mean, m2}` per metric. Variance = m2/(n-1) for n>1.
stderr = sqrt(variance / n). Gate requires `stderr>0` and z >= threshold.

