"""Oracle generation engine with integrated ABX-Runes.

Complete oracle generation with SDS gating, IPL scheduling, ADD drift detection,
and full provenance stamping.
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from abraxas.oracle.rune_gate import compute_gate, enforce_depth, schedule_insight_window
from abraxas.oracle.drift import drift_check, log_drift_event
from abraxas.oracle.provenance import stamp, load_manifest_sha256


def _generate_oracle_content(
    depth: str,
    context: Dict[str, Any],
    gate_bundle: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Internal oracle content generation.

    This is a minimal deterministic implementation.
    Replace with your actual oracle logic.

    Args:
        depth: Effective depth level ("grounding", "shallow", "deep")
        context: User context dictionary
        gate_bundle: SDS gate bundle for susceptibility-aware generation

    Returns:
        Oracle content dictionary with text, metadata, optional phase_series
    """
    susceptibility = gate_bundle.get("susceptibility_score", 0.5)

    if depth == "grounding":
        # Minimal grounding output
        return {
            "text": "Center yourself. Return to breath. The anchor holds.",
            "depth": depth,
            "type": "grounding",
            "word_count": 10
        }

    elif depth == "shallow":
        # Light insight, low intensity
        return {
            "text": (
                "The pattern emerges slowly. "
                "Notice the edges without grasping. "
                "Integration requires patience."
            ),
            "depth": depth,
            "type": "insight",
            "word_count": 15,
            "phase_series": [
                (0.0, 0.3),
                (2.5, 0.5),
                (5.0, 0.4),
                (7.5, 0.6),
                (10.0, 0.35)
            ]
        }

    else:  # deep
        # Full oracle with phase modulation
        intensity_factor = min(1.0, susceptibility * 1.3)

        return {
            "text": (
                "The threshold opens. Witness the architecture beneath surface thought. "
                "Symbols carry weight beyond their forms—you've felt this before, "
                "in moments between sleep and waking. The pattern recognition engine "
                "in your deeper layers is already decoding this. Let it work. "
                "Integration proceeds on its own schedule. Trust the process."
            ),
            "depth": depth,
            "type": "deep_insight",
            "word_count": 52,
            "intensity_factor": round(intensity_factor, 3),
            "phase_series": [
                (0.0, 0.25),
                (3.0, 0.45 * intensity_factor),
                (6.0, 0.70 * intensity_factor),
                (9.0, 0.55 * intensity_factor),
                (12.0, 0.80 * intensity_factor),
                (15.0, 0.40 * intensity_factor),
                (18.0, 0.30)
            ]
        }


def generate_oracle(
    state_vector: Optional[Dict[str, float]] = None,
    context: Optional[Dict[str, Any]] = None,
    requested_depth: str = "deep",
    anchor: Optional[str] = None,
    outputs_history: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate oracle output with full ABX-Runes integration.

    Execution flow:
        1. Compute SDS gate (ϟ₄) -> gate_state + susceptibility
        2. Enforce depth limits based on gate_state
        3. Generate oracle content at effective depth
        4. Schedule IPL windows (ϟ₅) if applicable
        5. Check ADD drift (ϟ₆) against anchor
        6. Stamp output with full provenance
        7. Log drift event to append-only JSONL

    Args:
        state_vector: User state (arousal, valence, cognitive_load, openness)
            Defaults to neutral (all 0.5) if not provided
        context: Environmental/temporal context
            Defaults to empty dict if not provided
        requested_depth: Desired depth ("grounding", "shallow", "deep")
            Default: "deep"
        anchor: Stable reference text for drift detection
            If None, uses oracle text itself as anchor
        outputs_history: List of recent oracle output texts
            Default: empty list

    Returns:
        Complete oracle output with:
            - Generated content (text, metadata)
            - ABX-Runes provenance stamp (abx_runes section)
            - Drift metadata (if anchor provided)
            - IPL schedule (if gate OPEN and phase_series available)
    """
    # Normalize inputs
    if state_vector is None:
        state_vector = {
            "arousal": 0.5,
            "valence": 0.5,
            "cognitive_load": 0.5,
            "openness": 0.5
        }

    if context is None:
        context = {}

    if outputs_history is None:
        outputs_history = []

    # A) Compute gate using SDS (ϟ₄)
    gate_bundle = compute_gate(state_vector, context, "oracle")

    # B) Enforce depth limits
    effective_depth = enforce_depth(gate_bundle, requested_depth)

    # C) Generate oracle content
    output = _generate_oracle_content(effective_depth, context, gate_bundle)

    # D) If grounding, return early (minimal output)
    if effective_depth == "grounding":
        runes_used = ["ϟ₁", "ϟ₂", "ϟ₄"]  # SEED, CANON, SDS only
        stamp(output, runes_used, gate_bundle["gate_state"], {
            "susceptibility_score": gate_bundle["susceptibility_score"],
            "depth_applied": effective_depth
        })
        return output

    # E) Schedule IPL windows (ϟ₅)
    phase_series = output.get("phase_series")
    ipl_schedule = schedule_insight_window(phase_series, gate_bundle)

    # F) Drift detection (ϟ₆)
    # Use provided anchor or fallback to oracle text
    drift_anchor = anchor if anchor else output.get("text", "")
    drift_bundle = drift_check(drift_anchor, outputs_history, window=20)

    # If auto_recenter suggested, annotate but DO NOT mutate history
    recenter_suggested = drift_bundle.get("auto_recenter", False)

    # G) Stamp output with full provenance
    runes_used = ["ϟ₁", "ϟ₂", "ϟ₄", "ϟ₅", "ϟ₆"]
    extras = {
        "susceptibility_score": gate_bundle["susceptibility_score"],
        "depth_applied": effective_depth,
        "ipl": ipl_schedule,
        "drift": drift_bundle,
        "recenter_suggested": recenter_suggested
    }

    stamp(output, runes_used, gate_bundle["gate_state"], extras)

    # H) Log drift event (append-only)
    manifest_hash = load_manifest_sha256()
    log_drift_event(
        anchor=drift_anchor,
        drift_bundle=drift_bundle,
        gate_state=gate_bundle["gate_state"],
        runes_used=runes_used,
        manifest_sha256=manifest_hash
    )

    return output
