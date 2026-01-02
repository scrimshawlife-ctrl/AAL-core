# LUMA Visualization Meta-Corpus (Scaffolding)

This folder is a scaffolding location for a provenance-aware visualization meta-corpus.

## Entry format

Each entry is a pair:

- `*.md`: human-readable description (no toy data; `not_computable` allowed)
- `*.json`: structured sidecar (shape + semantics + when-not-to-use)

## Sidecar schema (informal)

```json
{
  "id": "corpus:<stable-id>",
  "pattern_kind": "motif_graph|domain_lattice|...",
  "data_shape": "text description",
  "symbolic_meaning": "text description",
  "visual_mapping": {
    "position": "no meaning unless specified",
    "edge_thickness": "resonance_magnitude",
    "transparency": "uncertainty"
  },
  "when_not_to_use": ["..."],
  "failure_modes": ["..."],
  "provenance": {
    "source_frame_provenance": "not_computable",
    "evidence": "not_computable"
  }
}
```

## Templates

Start from `template_entry.md` + `template_entry.json` (provided) and replace all placeholders with real provenance.

