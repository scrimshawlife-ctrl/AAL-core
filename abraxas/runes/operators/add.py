"""ϟ₆ ADD: Anchor Drift Detection operator.

Detects semantic/thematic drift from a stable anchor across output history.
Triggers recentering suggestions when drift exceeds safe bounds.

No network calls. Deterministic string-based heuristics only.
"""

from __future__ import annotations
import hashlib
from typing import Any, Dict, List


def _text_features(text: str) -> Dict[str, float]:
    """Extract simple deterministic text features."""
    words = text.lower().split()
    chars = set(text.lower())

    return {
        "length": len(text),
        "word_count": len(words),
        "unique_chars": len(chars),
        "avg_word_len": sum(len(w) for w in words) / max(1, len(words)),
        "char_entropy": len(chars) / max(1.0, len(text))  # Simplified entropy
    }


def _drift_distance(anchor: str, target: str) -> float:
    """
    Compute drift distance between anchor and target text.
    Uses simple feature-based distance (no ML/embeddings).

    Returns: distance scalar in [0.0, 1.0+]
    """
    f_anchor = _text_features(anchor)
    f_target = _text_features(target)

    # Normalized feature distances
    dist = 0.0
    dist += abs(f_anchor["word_count"] - f_target["word_count"]) / max(f_anchor["word_count"], f_target["word_count"], 1)
    dist += abs(f_anchor["avg_word_len"] - f_target["avg_word_len"]) / max(f_anchor["avg_word_len"], f_target["avg_word_len"], 1.0)
    dist += abs(f_anchor["char_entropy"] - f_target["char_entropy"])

    # Simple string overlap check (jaccard-like)
    anchor_words = set(anchor.lower().split())
    target_words = set(target.lower().split())
    if anchor_words or target_words:
        overlap = len(anchor_words & target_words) / len(anchor_words | target_words)
        dist += (1.0 - overlap)

    return dist / 4.0  # Average of 4 components


def apply_add(
    anchor: str,
    outputs_history: List[str],
    window: int = 20,
    drift_threshold: float = 0.45,
    critical_threshold: float = 0.70
) -> Dict[str, Any]:
    """
    Detect drift from anchor across recent output history.

    Args:
        anchor: Stable reference text (theme, core motif, etc.)
        outputs_history: List of recent output strings (most recent last)
        window: Number of recent outputs to analyze
        drift_threshold: Drift magnitude that triggers warning
        critical_threshold: Drift magnitude that triggers auto-recenter suggestion

    Returns:
        {
            "drift_magnitude": float (0.0-1.0+),
            "drift_velocity": float (rate of change),
            "integrity_score": float (1.0 - drift_magnitude, clamped),
            "auto_recenter": bool,
            "status": "stable" | "drifting" | "critical",
            "anchor_hash": str (first 8 chars of SHA256),
            "samples_analyzed": int,
            "rune_id": "ϟ₆"
        }
    """
    if not anchor or not outputs_history:
        return {
            "drift_magnitude": 0.0,
            "drift_velocity": 0.0,
            "integrity_score": 1.0,
            "auto_recenter": False,
            "status": "stable",
            "anchor_hash": "",
            "samples_analyzed": 0,
            "rune_id": "ϟ₆"
        }

    # Analyze recent window
    recent = outputs_history[-window:]
    distances = [_drift_distance(anchor, output) for output in recent]

    # Compute metrics
    avg_drift = sum(distances) / len(distances) if distances else 0.0

    # Drift velocity: compare first half vs second half of window
    if len(distances) >= 4:
        mid = len(distances) // 2
        early_drift = sum(distances[:mid]) / mid
        late_drift = sum(distances[mid:]) / (len(distances) - mid)
        drift_velocity = late_drift - early_drift
    else:
        drift_velocity = 0.0

    # Determine status
    if avg_drift >= critical_threshold:
        status = "critical"
        auto_recenter = True
    elif avg_drift >= drift_threshold:
        status = "drifting"
        auto_recenter = False
    else:
        status = "stable"
        auto_recenter = False

    # Integrity score (inverse of drift, clamped)
    integrity = max(0.0, 1.0 - avg_drift)

    # Anchor hash for provenance
    anchor_hash = hashlib.sha256(anchor.encode("utf-8")).hexdigest()[:8]

    return {
        "drift_magnitude": round(avg_drift, 3),
        "drift_velocity": round(drift_velocity, 3),
        "integrity_score": round(integrity, 3),
        "auto_recenter": auto_recenter,
        "status": status,
        "anchor_hash": anchor_hash,
        "samples_analyzed": len(recent),
        "rune_id": "ϟ₆"
    }
