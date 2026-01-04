# AAL-GIMLET Documentation

**Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation**

Version: 0.1.0

---

## Overview

AAL-GIMLET is the canonical **ingress adapter** for AAL-core. It provides deterministic codebase analysis, classification, and integration planning.

### Purpose

GIMLET serves as the **front door** to AAL-core, ensuring:
- Deterministic analysis of any codebase
- Evidence-based classification
- Provenance-tracked operations
- Integration planning for AAL-native code
- Optimization roadmaps for external code

### Core Principles

1. **SEED Compliance**: All operations are deterministic with provenance tracking
2. **Evidence-Based**: No heuristics without explicit evidence
3. **ABX-Runes Integration**: Exposes `gimlet.v0.inspect` rune
4. **Complexity Must Pay Rent**: Scoring evaluates value vs. cost

---

## Operating Modes

GIMLET supports four operating modes:

| Mode | Description |
|------|-------------|
| `inspect` | Analyze codebase and produce report (default) |
| `integrate` | Validate and plan integration for AAL-native code |
| `optimize` | Generate optimization roadmap for external code |
| `report` | Produce human-readable report |

---

## Operating Flow

### Phase 1: Normalize Input

**Input**: Directory path OR zip file path

**Actions**:
- Extract zip deterministically (if applicable)
- Scan filesystem with exclusion patterns
- Compute file hashes (SHA256)
- Detect languages and entrypoints
- Build `FileMap` snapshot

**Output**: `FileMap` + `ProvenanceEnvelope`

**Determinism**:
- Files sorted by path
- Deterministic hash computation
- Reproducible with same inputs

---

### Phase 2: Identity Classification

**Rules**:

1. **AAL_OVERLAY**: Has `.aal/overlays/*/manifest.json`
2. **AAL_SUBSYSTEM**: Has `aal_core/` structure + canon patterns (≥0.3 confidence)
3. **EXTERNAL**: Everything else

**Evidence Tracking**:
- Each classification includes file-level evidence
- Confidence scores backed by specific rules
- No classification without evidence

---

### Phase 3: Integration or Optimization Planning

#### For AAL_OVERLAY / AAL_SUBSYSTEM:

**Integration Plan** includes:
- Missing tests detection
- Broken module boundaries (missing `__init__.py`)
- Naming violations (non-snake_case)
- Acronym compliance checks
- Estimated complexity (trivial, moderate, high)

#### For EXTERNAL:

**Optimization Roadmap** (3 phases):

**Phase 0 - Instrumentation + Provenance**
- Add deterministic I/O logging
- Implement provenance envelopes
- Create baseline metrics
- Track entropy sources

**Phase 1 - Rune Façade (Non-Invasive)**
- Identify stable API boundaries
- Create ABX-Runes façade layer
- Attach rune metadata
- Integrate with EventBus

**Phase 2 - Internal Modularization (Rent-Gated)**
- Analyze subsystem boundaries
- Apply complexity rent analysis
- Extract high-value subsystems
- Add stability tests

---

### Phase 4: GIMLET Scoring

**Total Score**: 0-100 points

#### Component Breakdown:

**Integratability (0-30)**
- AAL_OVERLAY: Base 25 points
- AAL_SUBSYSTEM: Base 20 points
- EXTERNAL: Base 5 points
- Deductions: -5 per critical error
- Bonus: +5 for test coverage

**Rune-Fit (0-30)**
- Existing rune usage: +15
- Modular structure: +10
- Clear API boundaries: +5

**Determinism Readiness (0-20)**
- Provenance patterns: +5
- Test presence: +5
- SEED patterns: +5
- Structured config: +5

**Rent Potential (0-20)**
- Large codebase (>10k LOC): +10
- Polyglot (≥3 languages): +5
- Clear subsystem boundaries: +5

---

### Phase 5: Result Assembly

**Output**: `InspectResult` with:
- `provenance`: Deterministic metadata
- `file_map`: Normalized filesystem
- `identity`: Classification + evidence
- `integration_plan`: (if AAL-native)
- `optimization_roadmap`: (if external)
- `score`: GIMLET score breakdown

**ABX-Runes Metadata** attached:
- `used`: `["gimlet.v0.inspect"]`
- `manifest_sha256`: Result hash
- `vendor_lock_sha256`: Determinism proof

---

## ABX-Runes Interface

### Rune: `gimlet.v0.inspect`

**Function Signature**:
```python
def inspect(
    source_path: str,
    mode: str = "inspect",
    run_seed: Optional[str] = None,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, Any]
```

**Parameters**:
- `source_path`: Path to directory or .zip file
- `mode`: Operating mode (inspect, integrate, optimize, report)
- `run_seed`: Optional deterministic seed for provenance
- `exclude_patterns`: Glob patterns to exclude (default: `*.pyc`, `__pycache__`, `.git`)

**Returns**:
```python
{
    "result": InspectResult,  # Full analysis
    "abx_runes": {            # Provenance metadata
        "used": ["gimlet.v0.inspect"],
        "gate_state": "active",
        "manifest_sha256": "...",
        "vendor_lock_sha256": "...",
        "provenance": {...}
    }
}
```

---

## Acronym Registry Enforcement

### Purpose

GIMLET enforces **descriptive acronym governance** across AAL-core:
- All subsystems MUST have expansions
- Non-canonical names are rejected
- Aliases are supported with warnings

### Canonical Subsystems

| Name | Expansion | Status |
|------|-----------|--------|
| AAL-ABX | Abraxas eXecution framework | active |
| AAL-SEED | Symbolic Entropy Elimination for Determinism | active |
| AAL-ERS | Evidence-based Runtime Stabilization | active |
| AAL-RUNE | Runtime Unit of Networked Execution | active |
| AAL-YGGDRASIL | YGGDRASIL Graph Dependency Resolution And Scheduling Infrastructure Layer | active |
| AAL-OSL | Overlay Service Layer | active |
| AAL-SCL | Self-Containment Layer | active |
| AAL-SHADOW | Safe Heuristic Analysis and Detection Of Warnings | active |
| AAL-IOL | Input/Output Ledger | active |
| AAL-VIZ | Visualization Intelligence Zone | active |
| AAL-GIMLET | Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation | active |
| AAL-IRIS | Intelligent Runtime Inspection System | active |

### Validation API

```python
from aal_core.adapters.gimlet import validate_subsystem_name

is_valid, warning = validate_subsystem_name("AAL-GIMLET")
# (True, None)

is_valid, warning = validate_subsystem_name("UNKNOWN")
# (False, "Non-canonical subsystem name: UNKNOWN")
```

---

## Usage Examples

### Example 1: Inspect External Codebase

```python
from aal_core.adapters.gimlet import inspect

result = inspect(
    source_path="/path/to/external-project",
    mode="inspect",
    run_seed="deterministic-seed-123"
)

print(f"Identity: {result['result']['identity']['kind']}")
print(f"Score: {result['result']['score']['total']}/100")
print(f"Roadmap: {len(result['result']['optimization_roadmap']['phases'])} phases")
```

### Example 2: Validate AAL Overlay

```python
result = inspect(
    source_path=".aal/overlays/my-overlay",
    mode="integrate"
)

issues = result['result']['integration_plan']['issues']
for issue in issues:
    print(f"{issue['severity']}: {issue['message']}")
```

### Example 3: Enforce Acronym Registry

```python
from aal_core.adapters.gimlet import validate_subsystem_name

subsystems = ["AAL-GIMLET", "AAL-ERS", "CUSTOM-MODULE"]

for name in subsystems:
    is_valid, warning = validate_subsystem_name(name)
    if not is_valid:
        print(f"ERROR: {name} is not canonical")
    elif warning:
        print(f"WARNING: {warning}")
```

---

## Testing Strategy

### Determinism Tests

**Requirement**: Same inputs → same outputs

```python
def test_determinism():
    result1 = inspect("./sample", run_seed="seed1")
    result2 = inspect("./sample", run_seed="seed1")
    assert result1 == result2
```

### Missing Input Handling

**Requirement**: Invalid inputs → `not_computable` + reason

```python
def test_missing_input():
    with pytest.raises(ValueError, match="source_path must be"):
        inspect("/nonexistent/path")
```

### Bounds Tests

**Requirement**: Scores stay within bounds

```python
def test_score_bounds():
    result = inspect("./sample")
    score = result['result']['score']
    assert 0.0 <= score['total'] <= 100.0
    assert 0.0 <= score['integratability']['score'] <= 30.0
```

### Dozen-Run Invariance

**Requirement**: 12 consecutive runs produce identical results

```python
def test_dozen_run_stability():
    results = [inspect("./sample", run_seed="stable") for _ in range(12)]
    hashes = [r['abx_runes']['manifest_sha256'] for r in results]
    assert len(set(hashes)) == 1  # All identical
```

---

## Integration with AAL-Core

### Function Registry

GIMLET exports `GIMLET_RUNE_DESCRIPTOR` for automatic registration:

```python
from aal_core.adapters.gimlet import EXPORTS

for descriptor in EXPORTS:
    print(descriptor['id'])  # gimlet.v0.inspect
```

### Event Bus Integration

Future versions will emit events:
- `gimlet.inspect.started`
- `gimlet.inspect.completed`
- `gimlet.classification.updated`

### Ledger Integration

Future versions will append to EvidenceLedger:
- Inspection provenance
- Classification evidence
- Score history

---

## Extension Points

### Custom Classification Rules

Add rules in `identity.py`:

```python
def _check_custom_pattern(files: List[FileInfo]) -> List[Evidence]:
    # Custom detection logic
    return evidence
```

### Custom Scoring Components

Add scorers in `score.py`:

```python
def _score_custom_dimension(file_map: FileMap) -> ScoreComponent:
    # Custom scoring logic
    return ScoreComponent(...)
```

---

## Governance

### Naming Conventions

- Module names: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private functions: `_leading_underscore`

### Immutability

All data contracts use `@dataclass(frozen=True)`:
- No mutations after creation
- Hash stability guaranteed
- Thread-safe by default

### Error Handling

- Validate inputs at boundaries
- Raise `ValueError` for invalid parameters
- No silent failures
- Include context in error messages

---

## Versioning

**Current Version**: `0.1.0`

**Schema Version**: `gimlet-result/0.1`

**Compatibility**:
- ABX-Runes: `rune-descriptor/0.1`
- YGGDRASIL: `yggdrasil-overlay/0.1`
- AAL-core: `0.1.x`

---

## Limitations

### Current MVP Limitations

1. **File Content Analysis**: Currently uses path/structure heuristics. Full parsing planned for v0.2.
2. **Manifest Validation**: TODO markers for schema validation against YGGDRASIL-IR.
3. **Auto-Fix**: Integration plan includes `auto_fixable` flag but no execution yet.
4. **Event Bus**: Not yet wired to AAL-core EventBus (planned).

### Planned Enhancements

- Parse Python AST for import analysis
- Validate YAML/JSON manifests against schemas
- Auto-apply trivial integration fixes
- Real-time EventBus notifications
- EvidenceLedger integration
- Multi-language support (Go, Rust, TypeScript)

---

## References

- **ABX-Runes**: `/abx_runes/yggdrasil/`
- **SEED**: `aal_core/governance/` (provenance patterns)
- **EvidenceLedger**: `aal_core/ledger/ledger.py`
- **Function Registry**: `aal_core/registry/function_registry.py`

---

## License

Part of AAL-core canonical subsystems.

**Status**: Active
**Maintainer**: AAL-core team
**Last Updated**: 2026-01-04
