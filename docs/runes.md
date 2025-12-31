# AAL-Core ABX-Runes Consumption Layer

## Overview

AAL-Core implements a **consumption-only** layer for ABX-Runes. This layer:

- **Consumes** vendored rune exports from Abraxas (source-of-truth)
- **Does NOT generate** sigils or rune definitions
- **Embeds** deterministic provenance hashes in all bus messages
- **Verifies** vendor integrity via hash-locked LOCK.json

## Architecture

```
Abraxas (Source)          AAL-Core (Consumer)
================          ===================
Generate sigils    --->   Import vendor bundle
Export registry    --->   Verify provenance
Build dist bundle  --->   Lock + hash verify
                          Attach to payloads
```

### Key Principle

**Abraxas is the source-of-truth for rune generation.**
AAL-Core only consumes pre-built, hash-verified export bundles.

## Directory Structure

```
src/aal_core/
├── vendor/
│   └── abx_runes/           # Vendored rune assets (imported)
│       ├── LOCK.json        # Hash-locked integrity file
│       ├── registry.json    # Rune metadata registry
│       ├── definitions/     # Rune definition files
│       └── sigils/          # SVG sigil files
│           └── manifest.json
├── runes/
│   ├── abx_runes.py        # Runtime accessor (list/get runes)
│   └── attach.py           # Provenance attachment helpers
├── schema/
│   └── resonance_frame.py  # ResonanceFrame schema
└── bus/
    └── frame.py            # Frame construction utilities
```

## Importing Vendored Runes

Use the vendor builder script to import rune bundles from Abraxas:

```bash
# Import a versioned export bundle (dry-run first)
python scripts/abx_runes_vendor_build.py --import /path/to/dist/abx-runes/v1.4

# Import with write (atomic swap)
python scripts/abx_runes_vendor_build.py --import /path/to/dist/abx-runes/v1.4 --write

# Verify lock integrity
python scripts/abx_runes_vendor_build.py --check
```

### What Gets Imported

The vendor builder:

1. **Verifies** export integrity via `export_provenance.json`
2. **Validates** all file SHA256 hashes
3. **Performs atomic swap** into `src/aal_core/vendor/abx_runes/`
4. **Generates** hash-locked `LOCK.json`
5. **Creates** runtime accessor if missing

## Provenance Hashes

All ResonanceFrame messages carry deterministic provenance anchors:

- **`vendor_lock_sha256`**: SHA256 of vendor LOCK.json (ensures version immutability)
- **`manifest_sha256`**: SHA256 of sigils/manifest.json (tracks sigil registry)

### Why Hash-Locking Matters

Provenance hashes enable:

- **Reproducibility**: Exact vendor state can be reconstructed
- **Audit trails**: Track which rune version was used in each message
- **Deterministic replay**: Replay bus invocations with correct rune context

## Usage Examples

### 1. Access Vendored Runes

```python
from aal_core.runes.abx_runes import list_runes, get_rune, get_sigil_svg, verify_lock

# Verify vendor integrity (recommended at startup)
result = verify_lock()
print(f"Vendor OK: {result['abx_runes_version']}")

# List all runes
runes = list_runes()
for r in runes:
    print(f"{r['id']}: {r['name']}")

# Get specific rune metadata
rune = get_rune("0001")
print(f"Rune: {rune['name']}")
print(f"Category: {rune['category']}")

# Get sigil SVG
svg = get_sigil_svg("0001")
```

### 2. Attach Rune Provenance to Payloads

```python
from aal_core.runes.attach import attach_runes

# Original payload
payload = {
    "phase": "OPEN",
    "data": {"prompt": "hello", "intent": "test"}
}

# Attach rune metadata with provenance hashes
payload_with_runes = attach_runes(
    payload,
    used=["0001", "0042"],  # Rune IDs consumed
    gate_state="SEAL",      # Current gate state
    extras={"oracle_mode": "active"}  # Optional extras
)

# Result includes:
# {
#   "phase": "OPEN",
#   "data": {...},
#   "abx_runes": {
#     "used": ["0001", "0042"],
#     "gate_state": "SEAL",
#     "manifest_sha256": "a3f5...",
#     "vendor_lock_sha256": "b8c2...",
#     "oracle_mode": "active"
#   }
# }
```

**Important**: `attach_runes()` does NOT mutate the original payload. It returns a shallow copy.

### 3. Create ResonanceFrame Messages

```python
from aal_core.bus.frame import make_frame

# Create a frame with automatic provenance injection
frame = make_frame(
    module="abraxas.overlay",
    payload={"phase": "OPEN", "data": {...}},
    abx_runes={
        "used": ["0001"],
        "gate_state": "CLEAR"
    }
)

# Frame structure:
# {
#   "utc": "2025-01-15T12:34:56.789Z",
#   "module": "abraxas.overlay",
#   "payload": {...},
#   "abx_runes": {...},
#   "provenance": {
#     "vendor_lock_sha256": "a3f5...",
#     "manifest_sha256": "b8c2..."
#   }
# }
```

## Vendor Lock Verification

The LOCK.json file contains:

```json
{
  "abx_runes_version": "v1.4",
  "generator_version": "abx_runes_vendor_build@1",
  "imported_at_utc": "2025-01-15T10:00:00Z",
  "manifest_sha256": "a3f5...",
  "files": [
    {"path": "registry.json", "sha256": "b8c2..."},
    {"path": "sigils/manifest.json", "sha256": "d7e9..."},
    ...
  ],
  "source_hint": "/path/to/dist/abx-runes/v1.4",
  "source_commit": "abc123..."
}
```

### Runtime Verification

```python
from aal_core.runes.abx_runes import verify_lock

# Verify all vendored files match their hashes
result = verify_lock()
# Raises ValueError if any hash mismatches
# Raises FileNotFoundError if files are missing
```

## Graceful Degradation

If vendor assets are missing:

- `make_frame()` still works (empty provenance)
- `attach_runes()` raises `FileNotFoundError`
- `verify_lock()` raises `FileNotFoundError`

This allows AAL-Core to function without runes in minimal configurations.

## Testing

Run the test suite:

```bash
# Run all rune-related tests
pytest tests/test_attach_runes.py -v
pytest tests/test_resonance_frame_provenance.py -v

# Or run all tests
pytest tests/ -v
```

Tests gracefully skip if vendor assets are missing (won't hard-fail CI).

## Integration with Overlay Bus

When invoking overlays via the bus, use `make_frame()` to create provenance-tracked messages:

```python
from aal_core.bus.frame import make_frame

# Create frame for overlay invocation
frame = make_frame(
    module="abraxas.overlay",
    payload={
        "phase": "OPEN",
        "data": {"prompt": "hello", "intent": "test"}
    },
    abx_runes={
        "used": ["0001", "0042"],
        "gate_state": "SEAL"
    }
)

# Log to provenance (logs/provenance.jsonl)
# Frame includes vendor_lock_sha256 + manifest_sha256 for audit trail
```

## Provenance Log Format

All frames logged to `logs/provenance.jsonl` include:

```json
{
  "utc": "2025-01-15T12:34:56.789Z",
  "module": "abraxas.overlay",
  "payload_sha256": "e4f8...",
  "payload": {...},  // If AAL_DEV_LOG_PAYLOAD=1
  "abx_runes": {
    "used": ["0001", "0042"],
    "gate_state": "SEAL",
    "manifest_sha256": "a3f5...",
    "vendor_lock_sha256": "b8c2..."
  },
  "provenance": {
    "vendor_lock_sha256": "b8c2...",
    "manifest_sha256": "a3f5..."
  }
}
```

## Workflow: Updating Runes

When Abraxas publishes a new rune export:

1. **Export** from Abraxas: `python scripts/abx_runes_export.py --write` (in Abraxas repo)
2. **Import** to AAL-Core: `python scripts/abx_runes_vendor_build.py --import /path/to/dist/abx-runes/v1.5 --write`
3. **Verify**: `python scripts/abx_runes_vendor_build.py --check`
4. **Test**: `pytest tests/ -v`
5. **Commit** LOCK.json + vendored assets

The new `vendor_lock_sha256` will automatically propagate to all future frames.

## Best Practices

1. **Always verify lock** at application startup:
   ```python
   from aal_core.runes.abx_runes import verify_lock
   verify_lock()  # Fail-fast if vendor is corrupted
   ```

2. **Never modify vendor assets** directly - always re-import from Abraxas

3. **Commit LOCK.json** to git for reproducibility

4. **Use `attach_runes()`** when rune context is known

5. **Use `make_frame()`** for all bus messages (automatic provenance)

6. **Log frames** to provenance.jsonl for audit trails

## Security Considerations

- **Hash verification** prevents tampering with vendored assets
- **Deterministic hashes** enable exact version tracking
- **No network calls** - all operations are offline
- **Stdlib only** - minimal attack surface
- **Lock file** acts as cryptographic seal on vendor state

## Troubleshooting

### FileNotFoundError: Missing LOCK.json

```bash
# Run vendor import first
python scripts/abx_runes_vendor_build.py --import /path/to/export --write
```

### ValueError: Hash mismatch

Vendor assets have been corrupted or modified. Re-import from source:

```bash
python scripts/abx_runes_vendor_build.py --import /path/to/export --write
```

### Tests skipping with "Vendor assets not present"

This is expected if vendor hasn't been imported yet. Tests are designed to skip gracefully.

## Summary

- **Abraxas**: Source-of-truth for rune generation
- **AAL-Core**: Consumes hash-verified vendor bundles
- **Provenance**: All frames carry `vendor_lock_sha256` + `manifest_sha256`
- **Deterministic**: No network calls, reproducible hashes, atomic swaps
- **Audit-ready**: Full provenance trail in logs

For rune generation and sigil creation, see Abraxas repository documentation.
