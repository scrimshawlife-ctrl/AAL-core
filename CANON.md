# Canon Diffs Ledger

## Overview

This document tracks architectural changes and invariant modifications to AAL-Core.

## Version 1.0.0 - Initial Release

### Changes
- **Wired Abraxas overlay as external module executed via AAL-Core overlay shim**
  - No capability changes
  - No invariant changes
  - Overlay execution isolated via subprocess with timeout enforcement
  - Provenance logging enabled with payload hashing for replay capability

### Architecture

```
AAL-Core Bus (FastAPI)
├── /invoke/{overlay} endpoint
├── Overlay manifest loading (.aal/overlays/*/manifest.json)
├── Subprocess execution with timeout
└── Append-only provenance logging (logs/provenance.jsonl)

Abraxas Overlay
├── Four phases: OPEN, ALIGN, CLEAR, SEAL
├── Analysis capability only
└── 2.5s timeout
```

### Guarantees

1. **Append-only provenance**: All invocations logged to `logs/provenance.jsonl`
2. **Payload hashing**: SHA256 hash computed for replay verification
3. **Phase validation**: Invalid phases rejected at bus level
4. **Timeout enforcement**: Overlays killed after manifest-specified timeout
5. **Isolation**: Overlays execute in subprocess, cannot corrupt bus state

### Testing

- Bus-only regression tests prevent spine breakage
- All four Abraxas phases tested
- Provenance logging verified
- Invalid phase rejection tested

## Changelog

### 2025-12-15
- Initial AAL-Core bus implementation
- Abraxas overlay integration (v2.1)
- Provenance logging with payload hash + full payload (dev mode)
- Test suite for bus invocation
