# LUMA Visual Semantics (Canonical Law)

LUMA encodes *meaning* as data in `LumaSceneIR`. Renderers may choose a visual style, but **must not change semantics**.

## Core semantics

- **Position**: position is *layout only* and has **no meaning** unless a pattern explicitly states a positional semantics (e.g. domain layering).
- **Edge thickness**: thickness represents **resonance magnitude** (`SceneEdge.resonance_magnitude`) when available.
- **Edge color family**: color represents **domain family** (`domain` field).
- **Motion**: motion represents **state change only** (e.g. temporal steps). No motion implies no state change semantics.
- **Transparency**: transparency represents **uncertainty** (`uncertainty` fields).
- **Decay**: decay animation (if present) represents **signal halflife**, never “importance”.
- **Glyphs**: glyph references must be **ABX-Runes only** (`glyph_rune_id == "0001"` etc). If unavailable: `not_computable`.

## Evidence gating

LUMA may show correlation-like structure (synchronicity/resonance edges), but it **must not** imply:

- causality
- prediction
- intervention recommendations

## Enforcement

`pipeline/validate_scene.py` enforces:

- explicit `not_computable`
- uncertainty in \([0,1]\)
- magnitude non-negative
- glyph IDs match ABX-Runes ID format

