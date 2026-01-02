# AAL VizIR

Render-agnostic visualization IR for AAL. VizIR is deterministic, composable, and auditable.

## Goals
- Render-agnostic: SVG now, Canvas/WebGL later.
- Deterministic ordering and rounding at the IR boundary.
- Composable overlays via layers.
- Auditable provenance metadata.

## Layout
- `src/schema`: JSON Schema for VizIR.
- `src/types`: TypeScript types.
- `src/emit`: IR emitters (scene/overlays/trends).
- `src/render`: SVG renderer and fallbacks.
- `src/utils`: sorting, rounding, provenance helpers.

## Notes
Emitters never import renderers. Renderers only consume VizIR.
