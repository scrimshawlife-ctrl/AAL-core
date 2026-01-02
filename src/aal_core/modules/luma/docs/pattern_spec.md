# LUMA Pattern Spec (v1)

Patterns are composable semantic projections from a `ResonanceFrame.payload` into `LumaSceneIR`.

Each pattern defines:

- **Input contract** (required payload keys/shapes)
- **Required metrics** (if any)
- **Failure modes** (explicit, deterministic)
- **Visual affordances** (semantic hints, not styling)
- **Deterministic algorithm** (no hidden randomness; only `seed`)

## Builtins

### Motif Graph (`motif_graph/v1`)

- **Nodes**: motifs
- **Edges**: synchronicity/resonance (optional)
- **Failure**: `no_motifs`

### Domain Lattice (`domain_lattice/v1`)

- **Entities**: domain + subdomain tiles (no edges)
- **Failure**: `no_domains`

### Temporal Braid (`temporal_braid/v1`)

- **Entities**: motif strands
- **Time axis**: discrete steps
- **Animation plan**: `timeline`
- **Failure**: `no_timeline`

#### Temporal Braid (static SVG band)

**Purpose:** Make time legible as a multi-lane braid of motif activity.

**Inputs (payload):**
- `timeline`: `list[{t, motifs}]`
  - `t`: epoch seconds (`int|float`) or ISO timestamp string (UTC assumed if no tz)
  - `motifs`: `list[str]` motif identifiers (names)

**Visual semantics (static renderer):**
- X-axis encodes time across the provided timeline steps.
- Each lane corresponds to a motif (from `payload.motifs`).
- Each step is a vertical “knot”; motif presence at a step is shown by a lane tick.
- No implied causality; braid expresses temporal co-occurrence only.

### Resonance Field (`resonance_field/v1`)

- **Fields**: scalar field grid
- **Failure**: `no_field` / `not_computable`

### Sankey Transfer (`sankey_transfer/v1`)

- **Entities**: domains
- **Edges**: transfers (width=value semantics)
- **Failure**: `no_flows`

### Cluster Bloom (`cluster_bloom/v1`)

- **Entities**: clusters + motifs
- **Edges**: containment
- **Semantics**: decay/halflife (if provided)
- **Failure**: `no_motifs`

