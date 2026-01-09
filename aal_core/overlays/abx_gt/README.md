# ABX-GT Overlay v0.1 — Game Theory Instrumentation Pack (SHADOW)
Purpose:
- Deterministic game-theory simulation vectors for incentive/coordination diagnostics.
- Outputs are SHADOW-only: observe, log, annotate. Never govern forecasts.

Inputs:
- GTVector.v0 (see schema/gtvector.v0.json)

Outputs:
- ABXGTReport.v0 (defined here as a minimal stable envelope):
  {
    "overlay":"abx_gt",
    "version":"0.1",
    "lane":"shadow",
    "not_computable": false,
    "missing": [],
    "scores": {
      "coordination_pressure": 0..1,
      "defection_risk": 0..1,
      "equilibrium_stability": 0..1,
      "hidden_player_likelihood": 0..1,
      "payoff_opacity_index": 0..1,
      "signal_cost_ratio": 0..1,
      "credibility_decay_rate": 0..1
    },
    "provenance": {
      "seed": <int>,
      "vector_id": "<string>",
      "hash": "<sha256 of normalized input + version>"
    }
  }

Rules:
- Determinism required: same seed + same vector => identical output.
- Missing required fields => not_computable=true and list missing keys.
- No external data calls. No time dependence. No randomness beyond seed.

How to run:
- python -m aal_core.overlays.abx_gt.runtime.abx_gt_runner --vectors aal_core/overlays/abx_gt/vectors/abx_gt_vectors.v0.1.jsonl

How to couple:
- ABX-Runes overlay registry should treat this as optional install.
- Abraxas may attach output under oracle.shadow.abx_gt if installed.
