# LUMA — Lucid Universal Motif Animator

Canonical visualization projection layer for AAL / Abraxas symbolic state.

## Purpose

LUMA provides a **deterministic**, **provenance-aware** pipeline:

`ResonanceFrame` → `LumaSceneIR` → `RenderArtifact[]`

LUMA renders symbolic structure (motifs, domains, resonance, temporal evolution) into:

- Static SVG (v1)
- HTML canvas (interactive stub, v1)
- Animation plan JSON (v1)

## Non-goals

- **No analysis**: LUMA MUST NOT influence analysis or prediction.
- **No implied causality**: LUMA is evidence-gated and never asserts causality.
- **No generative art**: the ideation engine proposes grammars; it does not generate art.

## Guarantees (canon-aligned)

- **Determinism**: same input frame → same IR → same render (within numeric tolerances).
- **Explicit missingness**: missing data is represented as `not_computable`.
- **Provenance embedded**: all artifacts embed source frame anchors and scene hash.
- **ABX-Runes glyphs only**: glyph identifiers must be ABX-Runes IDs (e.g. `0001`) or `not_computable`.

## Integration

```python
from aal_core.modules.luma import render

artifacts = render(
    resonance_frame,
    mode="static",               # "static" | "interactive" | "animated"
    pattern_overrides=None,      # optional list of pattern kind strings
    exploration=False,           # if True, include ideation proposals in IR
)
```

## Example flows

- **Abraxas overlays**: a module emits a `ResonanceFrame` with motif/domain structure; LUMA produces a stable SVG “instrument panel”.
- **PatchHive** (future): PatchHive can skin LUMA outputs (styling only) without changing semantics or IR.

## Future extraction to `aal-vis`

Design notes:

- Implementation is self-contained under `src/aal_core/modules/luma/`.
- Coupling is limited to the `ResonanceFrame` shape (TypedDict/pydantic accepted).
- Renderers are backend modules; replacing them does not change scene semantics.

