"""Oracle anchor drift detection and logging.

Integrates ADD (ϟ₆) drift detection with append-only provenance logging.
"""

from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from abraxas.runes.operators.add import apply_add


DRIFT_LOG_PATH = Path(__file__).parent.parent.parent / "data" / "logs" / "anchor_drift.log.jsonl"


def drift_check(
    anchor: str,
    outputs_history: List[str],
    window: int = 20,
    drift_threshold: float = 0.45,
    critical_threshold: float = 0.70
) -> Dict[str, Any]:
    """
    Check for drift from anchor using ADD (ϟ₆).

    Args:
        anchor: Stable reference text (theme, motif, etc.)
        outputs_history: List of recent output strings
        window: Number of recent outputs to analyze (default: 20)
        drift_threshold: Warning threshold (default: 0.45)
        critical_threshold: Critical/recenter threshold (default: 0.70)

    Returns:
        ADD drift bundle with drift_magnitude, status, auto_recenter, etc.
    """
    return apply_add(
        anchor=anchor,
        outputs_history=outputs_history,
        window=window,
        drift_threshold=drift_threshold,
        critical_threshold=critical_threshold
    )


def log_drift_event(
    anchor: str,
    drift_bundle: Dict[str, Any],
    gate_state: str,
    runes_used: List[str],
    manifest_sha256: str
) -> None:
    """
    Append drift event to anchor_drift.log.jsonl.

    Creates log file and directory if they don't exist.
    Appends one JSON line per call (append-only).

    Args:
        anchor: Anchor text used
        drift_bundle: Output from drift_check()
        gate_state: Current SDS gate state
        runes_used: List of rune IDs applied
        manifest_sha256: Hash of ABX-Runes manifest
    """
    # Ensure log directory exists
    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Build log entry
    log_entry = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "anchor": anchor[:100],  # Truncate for log size
        "drift_magnitude": drift_bundle.get("drift_magnitude", 0.0),
        "drift_velocity": drift_bundle.get("drift_velocity", 0.0),
        "integrity_score": drift_bundle.get("integrity_score", 1.0),
        "auto_recenter": drift_bundle.get("auto_recenter", False),
        "status": drift_bundle.get("status", "stable"),
        "anchor_hash": drift_bundle.get("anchor_hash", ""),
        "samples_analyzed": drift_bundle.get("samples_analyzed", 0),
        "gate_state": gate_state,
        "runes_used": runes_used,
        "manifest_sha256": manifest_sha256
    }

    # Append to log (one JSON object per line)
    with DRIFT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
