# Portfolio Optimizer v0.4 (Greedy “knapsack-lite”)

This doc snapshots the deterministic v0.4 global allocation mechanism.

## Goal
Given:
- registry-discovered `TuningEnvelope`s (per module)
- live `MetricsEnvelope`s (optional, used upstream to estimate impacts)
- a set of candidate knob changes with estimated impact vectors

Select a **portfolio** of knob changes that maximizes a global objective under budgets/caps, then emit:
- one `PortfolioTuningIR` bundle
- one module-level `TuningIR` per module for ERS hot-apply

## Candidate shape (conceptual)
Each candidate knob change has an estimated impact vector:
- Δlatency_ms_p95
- Δcost_units
- Δerror_rate
- Δthroughput_per_s

And targets a concrete module/node + knob assignment.

## Scoring
The optimizer converts impact to a scalar:

\[
score = w_L \cdot \Delta latency + w_C \cdot \Delta cost + w_E \cdot \Delta error + w_T \cdot \Delta throughput
\]

Higher score is “better”. You choose signs via weights (e.g. if lower latency is better, set \(w_L < 0\)).

## Constraints (v0.4)
- **max_total_cost_units**: sum of positive Δcost_units (budget “spend”) must not exceed cap
- **max_total_latency_ms_p95**: sum of positive Δlatency_ms_p95 (budget “spend”) must not exceed cap
- **max_changes_per_cycle**: max number of selected knob changes
- **gates**:
  - no `TuningEnvelope` → excluded (“no envelope → no candidate”)
  - capability denied per knob → excluded
  - stabilization window active per knob → excluded

Budget rule v0.4 is conservative: **only positive deltas consume budget** (negative deltas do not “refund” budget).

## Algorithm (deterministic greedy)
1. Filter candidates by envelope + capability + stabilization, and ensure each candidate’s one-knob `TuningIR` would validate against the envelope (typed/bounded).
2. Compute score for each remaining candidate.
3. Sort candidates by:
   - score descending
   - then stable tie-break: `(module_id, node_id, knob_name, proposed_value)`
4. Greedily pick in that order until budgets/caps are hit.
5. Merge selected knob changes into **one module-level `TuningIR` per module**.

Complexity: \(O(N \log N)\) for \(N\) candidates.

## Promotion / evidence
v0.4 output is primarily **`applied_tune`** (hot-apply, not promoted).
The portfolio may tag candidates as “promotion candidates”, but **must not auto-promote** without evidence (promotion remains the existing v0.2 flow).

