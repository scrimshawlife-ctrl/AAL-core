# AAL-Core Acronym Registry

**Version**: 1.0.0
**Last Updated**: 2026-01-04
**Status**: Canonical

---

## Purpose

This registry defines **all canonical subsystem acronyms** in AAL-core.

### Governance Rules

1. **Every subsystem MUST have a descriptive acronym expansion**
2. **Non-canonical subsystem names are INVALID**
3. **Aliases are permitted but must reference canonical names**
4. **Deprecated subsystems remain in registry with status flag**

### Enforcement

The AAL-GIMLET subsystem enforces this registry:
- `validate_subsystem_name()` - Validates names against registry
- `enforce_registry_on_manifest()` - Validates overlay manifests
- Registration of non-canonical names is rejected

---

## Canonical Subsystems

### Active Subsystems

| Canonical Name | Expansion | Functional Definition | Location |
|----------------|-----------|----------------------|----------|
| **AAL-ABX** | **A**braxas e**X**ecution framework | Four-phase ritual execution pattern (OPEN, ALIGN, CLEAR, SEAL) | `abraxas/` |
| **AAL-SEED** | **S**ymbolic **E**ntropy **E**limination for **D**eterminism | Deterministic entropy management and provenance tracking | Throughout |
| **AAL-ERS** | **E**vidence-based **R**untime **S**tabilization | Runtime tuning system with promotion governance and effect tracking | `aal_core/ers/` |
| **AAL-RUNE** | **R**untime **U**nit of **N**etworked **E**xecution | Executable unit with deterministic coupling and promotion states | `aal_core/runes/`, `abx_runes/` |
| **AAL-GRIM** | **G**overned **R**une **I**ndex & **M**emory | Canonical rune catalog with governance and graph validation | `src/aal_core/grim/`, `.aal/grim/` |
| **AAL-YGGDRASIL** | **Y**GGDRASIL **G**raph **D**ependency **R**esolution **A**nd **S**cheduling **I**nfrastructure **L**ayer | Metadata-first topology layer for ABX-Runes execution planning | `abx_runes/yggdrasil/` |
| **AAL-OSL** | **O**verlay **S**ervice **L**ayer | Integration layer for external services and overlay manifests | `aal_core/integrations/`, `.aal/overlays/` |
| **AAL-SCL** | **S**elf-**C**ontainment **L**ayer | Capability gating and containment controls for alignment | `aal_core/alignment/` |
| **AAL-SHADOW** | **S**afe **H**euristic **A**nalysis and **D**etection **O**f **W**arnings | Observation-only monitoring lane for validation without execution | Throughout (lane="shadow") |
| **AAL-IOL** | **I**nput/**O**utput **L**edger | Append-only evidence ledger with deterministic serialization | `aal_core/ledger/` |
| **AAL-VIZ** | **V**isualization **I**ntelligence **Z**one | Pattern-based visualization and scene rendering (Luma) | `src/aal_core/modules/luma/` |
| **AAL-GIMLET** | **G**ateway for **I**ntegration, **M**odularization, **L**egibility, **E**valuation, and **T**ransformation | Deterministic ingress adapter for codebase analysis and integration | `aal_core/adapters/gimlet/` |
| **AAL-IRIS** | **I**ntelligent **R**untime **I**nspection **S**ystem | Runtime introspection and diagnostic interface | Planned |

---

### Aliases

| Alias | Canonical Name | Status | Notes |
|-------|----------------|--------|-------|
| **ABX** | AAL-ABX | alias | Short form for Abraxas |
| **ERS** | AAL-ERS | alias | Short form for ERS |

---

### Deprecated Subsystems

| Name | Expansion | Deprecated Since | Replacement |
|------|-----------|------------------|-------------|
| _(none)_ | - | - | - |

---

## Subsystem Descriptions

### AAL-ABX (Abraxas eXecution framework)

**Expansion**: Abraxas eXecution framework
**Status**: Active
**Location**: `abraxas/`

Four-phase ritual execution pattern:
- **OPEN**: Initialize context and establish boundaries
- **ALIGN**: Synchronize state and validate preconditions
- **CLEAR**: Execute core logic with monitoring
- **SEAL**: Finalize results and emit provenance

---

### AAL-SEED (Symbolic Entropy Elimination for Determinism)

**Expansion**: Symbolic Entropy Elimination for Determinism
**Status**: Active
**Location**: Throughout (principle, not module)

Deterministic entropy management:
- Provenance tracking for all operations
- Entropy source identification
- Deterministic seeding for reproducibility
- Vendor lock hashing for immutability

---

### AAL-ERS (Evidence-based Runtime Stabilization)

**Expansion**: Evidence-based Runtime Stabilization
**Status**: Active
**Location**: `aal_core/ers/`

Runtime tuning with governance:
- Effect tracking (running statistics)
- Promotion policies (candidate → promoted)
- Safe set construction (validated configurations)
- Baseline signature ordering (determinism)

---

### AAL-RUNE (Runtime Unit of Networked Execution)

**Expansion**: Runtime Unit of Networked Execution
**Status**: Active
**Location**: `aal_core/runes/`, `abx_runes/`

Executable units with:
- Deterministic coupling (ABX-Runes attachment)
- Promotion states (candidate, promoted, deprecated)
- Provenance metadata
- Realm/Lane topology (YGGDRASIL)

---

### AAL-GRIM (Governed Rune Index & Memory)

**Expansion**: Governed Rune Index & Memory
**Status**: Active
**Location**: `src/aal_core/grim/`, `.aal/grim/`

Canonical rune catalog governance:
- Deterministic catalog persistence
- Manifest discovery and normalization
- Graph integrity validation (dangling edges, orphans)
- Append-only governance with archival support

---

### AAL-YGGDRASIL (YGGDRASIL Graph Dependency Resolution And Scheduling Infrastructure Layer)

**Expansion**: YGGDRASIL Graph Dependency Resolution And Scheduling Infrastructure Layer
**Status**: Active
**Location**: `abx_runes/yggdrasil/`

Metadata-first topology:
- Manifest validation and planning
- Execution DAG construction
- Authority tree resolution
- Realm/Lane/NodeKind taxonomy
- Evidence integration

---

### AAL-OSL (Overlay Service Layer)

**Expansion**: Overlay Service Layer
**Status**: Active
**Location**: `aal_core/integrations/`, `.aal/overlays/`

Integration layer:
- Overlay manifest management
- External service adapters
- Function registry aggregation
- Remote endpoint discovery

---

### AAL-SCL (Self-Containment Layer)

**Expansion**: Self-Containment Layer
**Status**: Active
**Location**: `aal_core/alignment/`

Alignment and containment:
- Capability gating
- Objective firewall
- Self-modification controls
- Tripwire detection

---

### AAL-SHADOW (Safe Heuristic Analysis and Detection Of Warnings)

**Expansion**: Safe Heuristic Analysis and Detection Of Warnings
**Status**: Active
**Location**: Throughout (lane="shadow")

Observation-only monitoring:
- Shadow lane execution (no side effects)
- Validation without modification
- Compliance detection
- Drift analysis

**Principle**: Shadow ≠ Prediction (observation-only)

---

### AAL-IOL (Input/Output Ledger)

**Expansion**: Input/Output Ledger
**Status**: Active
**Location**: `aal_core/ledger/`

Append-only evidence:
- JSONL serialization
- Deterministic ordering
- Provenance per entry
- Schema versioning

---

### AAL-VIZ (Visualization Intelligence Zone)

**Expansion**: Visualization Intelligence Zone
**Status**: Active
**Location**: `src/aal_core/modules/luma/`

Pattern-based visualization:
- AutoViewIR (smart views)
- Pattern registry (MotifGraph, TemporalBraid, etc.)
- SVG rendering
- Canary governance
- Scene export

---

### AAL-GIMLET (Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation)

**Expansion**: Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation
**Status**: Active
**Location**: `aal_core/adapters/gimlet/`

Deterministic ingress adapter:
- Codebase classification (AAL_OVERLAY, AAL_SUBSYSTEM, EXTERNAL)
- Evidence-based identity detection
- Integration planning (AAL-native)
- Optimization roadmaps (external)
- GIMLET scoring (0-100)
- Acronym registry enforcement

**Role**: Front door to AAL-core. Nothing enters canon without passing through GIMLET.

---

### AAL-IRIS (Intelligent Runtime Inspection System)

**Expansion**: Intelligent Runtime Inspection System
**Status**: Active (Planned)
**Location**: Planned

Runtime introspection:
- Live state inspection
- Diagnostic interfaces
- Performance profiling
- Event stream monitoring

---

## Registry Schema

### AcronymDefinition Schema

```python
@dataclass(frozen=True)
class AcronymDefinition:
    canonical_name: str              # e.g., "AAL-GIMLET"
    expansion: str                   # Full acronym expansion
    functional_definition: str       # One-line purpose
    status: Literal["active", "deprecated", "alias"]
    alias_for: Optional[str] = None  # If status == "alias"
```

### Validation Rules

1. **canonical_name**: Must be uppercase, hyphen-separated
2. **expansion**: Must match acronym letters (case-insensitive)
3. **functional_definition**: Max 200 characters
4. **status**: Must be one of: active, deprecated, alias
5. **alias_for**: Required if status == "alias", must reference active subsystem

---

## Usage

### Validation

```python
from aal_core.adapters.gimlet import validate_subsystem_name

# Valid canonical name
is_valid, warning = validate_subsystem_name("AAL-GIMLET")
# Returns: (True, None)

# Alias (valid with warning)
is_valid, warning = validate_subsystem_name("ABX")
# Returns: (True, "Warning: ABX is an alias for AAL-ABX")

# Non-canonical (invalid)
is_valid, warning = validate_subsystem_name("CUSTOM-SUBSYSTEM")
# Returns: (False, "Non-canonical subsystem name: CUSTOM-SUBSYSTEM")
```

### Lookup

```python
from aal_core.adapters.gimlet import get_definition

defn = get_definition("AAL-GIMLET")
print(defn.expansion)
# "Gateway for Integration, Modularization, Legibility, Evaluation, and Transformation"
```

### Manifest Enforcement

```python
from aal_core.adapters.gimlet import enforce_registry_on_manifest

manifest = {
    "overlay": {"id": "custom-overlay"},
    "runes": [{"id": "custom.rune.v1"}]
}

errors = enforce_registry_on_manifest(manifest)
# Returns: ["Non-canonical overlay ID: custom-overlay", ...]
```

---

## Maintenance

### Adding New Subsystems

1. Add definition to `aal_core/adapters/gimlet/registry.py` in `_CANONICAL_DEFINITIONS`
2. Update this registry document
3. Add tests in `aal_core/adapters/gimlet/tests/test_registry.py`
4. Update GIMLET documentation

### Deprecating Subsystems

1. Change `status="deprecated"` in registry
2. Move to Deprecated section in this document
3. Document replacement/migration path
4. Add deprecation warnings to validation

### Creating Aliases

1. Add alias definition with `status="alias"` and `alias_for=<canonical>`
2. Add to Aliases section in this document
3. Ensure canonical name remains primary

---

## References

- **GIMLET Implementation**: `aal_core/adapters/gimlet/registry.py`
- **Validation API**: `aal_core/adapters/gimlet/__init__.py`
- **YGGDRASIL Schema**: `abx_runes/yggdrasil/schema.py`
- **Overlay Manifests**: `.aal/overlays/*/manifest.json`

---

## Versioning

**Registry Version**: 1.0.0

**Changes**:
- 1.0.0 (2026-01-04): Initial canonical registry with 12 subsystems

---

## Governance Authority

**Maintained By**: AAL-core team
**Approval Required**: All additions/changes require GIMLET validation
**Enforcement**: Automatic via `validate_subsystem_name()`

---

**END OF REGISTRY**
