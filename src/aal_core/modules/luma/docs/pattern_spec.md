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

