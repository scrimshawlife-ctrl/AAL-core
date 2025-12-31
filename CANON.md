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

### 2025-12-15 - Capability Enforcement (ASCEND/exec)
- **Added abraxas_exec overlay variant with 'exec' capability**
  - Declares both 'analysis' and 'exec' capabilities
  - Includes ASCEND phase for exec-capable operations
  - Points to same abraxas overlay code via symlink
- **ASCEND phase handler added to abraxas overlay**
  - Simulates exec operations (hash computation)
  - Only accessible to overlays declaring ASCEND in phases
- **Capability enforcement tests (5 new tests, 16/16 passing)**
  - test_ascend_allowed_for_exec_capable_overlay
  - test_ascend_blocked_for_analysis_only_overlay
  - test_exec_overlay_lists_ascend_phase
  - test_analysis_overlay_does_not_list_ascend
  - test_exec_overlay_can_use_clear_phase
- **Proves capability enforcement at manifest level**
  - Overlays can only use phases declared in manifest
  - Phase validation happens at bus level (400 error if invalid)
  - Read-only overlays cannot access exec phases

### 2025-12-15 - Replay Upgrade
- **Payload logging now controlled by AAL_DEV_LOG_PAYLOAD env var**
  - Default (production): Only SHA256 payload hash logged
  - Dev mode (AAL_DEV_LOG_PAYLOAD=1): Full payload logged for exact replay
- **Added TOOLS/replay.py for deterministic replay**
  - Replays exact payload from provenance log
  - Validates manifest hasn't drifted (optional warning)
  - Refuses replay if payload missing (directs user to enable dev mode)
- **Enhanced test suite**
  - Added test_dev_mode_payload_logging
  - Added test_replay_functionality
  - 7/7 tests passing

### 2025-12-15
- Initial AAL-Core bus implementation
- Abraxas overlay integration (v2.1)
- Provenance logging with payload hash + full payload (dev mode)
- Test suite for bus invocation
