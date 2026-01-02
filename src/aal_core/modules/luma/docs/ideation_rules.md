# LUMA Ideation Rules (v1)

The ideation engine proposes *visualization grammars* when baseline patterns fail to express structure.

## Critical constraints

- **Proposals are never defaults**.
- **No generative art**: proposals are compositions of existing primitives.
- **Deterministic**: same inputs → same proposals and scores.
- **Evidence-gated**: proposals must not imply causality.

## Proposal shape

A proposal includes:

- **Composition**: which existing `PatternKind` primitives to combine
- **Semantic justification**: what new meaning is expressed
- **Readability risks**: cognitive hazards / misreadings
- **Scores**:
  - information gain
  - cognitive load
  - redundancy vs baseline

## Governance knobs

`IdeationConstraints.v1_default()` controls:

- maximum allowed cognitive load
- minimum information gain
- maximum redundancy
- forbids new primitives

