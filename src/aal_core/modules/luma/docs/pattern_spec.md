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

- **Purpose**: establish a stable visual coordinate system for domain/subdomain structure.
- **Entities**: domain + subdomain tiles (no edges)
- **Constraints (optional)**:
  - `constraints.domain_order: [domain_id...]`
  - `constraints.subdomain_order: { domain_id: [subdomain_id...] }`
- **Visual semantics (canonical)**:
  - Each domain is a column (left-to-right)
  - Subdomains stack top-to-bottom inside the domain column
  - The lattice is an instrumentation layer; it must not imply importance unless explicitly encoded via scene semantics.
- **Failure**:
  - `no_domains` (empty domain set)

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

### Motif×Domain Heatmap (`motif_domain_heatmap/v1`)

- **Rows**: motifs (salience desc, then id)
- **Columns**: domains (sorted by id)
- **Cell value**: motif salience when motif.domain matches domain, else 0
- **Semantics**: opacity encodes salience, bounded [0.05, 0.9]
- **Failure**: `no_motifs` / `no_domains`

### Transfer Chord (`transfer_chord/v1`)

- **Entities**: domains (ring layout)
- **Edges**: transfer arcs aggregated by (source_domain, target_domain)
- **Semantics**: arc thickness/opacity encode transfer magnitude
- **Failure**: `no_flows`
