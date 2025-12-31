#!/usr/bin/env python3
"""Oracle CLI with ABX-Runes integration.

Run oracle generation from command line with JSON input files or inline args.

Examples:
    # Minimal usage (defaults)
    python scripts/run_oracle_with_runes.py

    # With state vector from file
    python scripts/run_oracle_with_runes.py --state state.json

    # With context from file
    python scripts/run_oracle_with_runes.py --context context.json

    # Inline args
    python scripts/run_oracle_with_runes.py --depth shallow --anchor "core theme"

    # Full example
    python scripts/run_oracle_with_runes.py \\
        --state state.json \\
        --context context.json \\
        --depth deep \\
        --anchor "pattern recognition" \\
        --history outputs.json
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from abraxas.oracle.engine import generate_oracle


def load_json_file(path: str) -> Any:
    """Load and parse JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate oracle output with ABX-Runes integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--state",
        type=str,
        help="Path to JSON file with state_vector (arousal, valence, cognitive_load, openness)"
    )

    parser.add_argument(
        "--context",
        type=str,
        help="Path to JSON file with context (time_of_day, session_count, etc.)"
    )

    parser.add_argument(
        "--depth",
        type=str,
        choices=["grounding", "shallow", "deep"],
        default="deep",
        help="Requested depth level (default: deep)"
    )

    parser.add_argument(
        "--anchor",
        type=str,
        help="Anchor text for drift detection (default: use oracle text)"
    )

    parser.add_argument(
        "--history",
        type=str,
        help="Path to JSON file with outputs_history (list of strings)"
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (default: compact)"
    )

    parser.add_argument(
        "--show-drift-log",
        action="store_true",
        help="Show last 5 lines of drift log after generation"
    )

    args = parser.parse_args()

    # Load inputs
    state_vector: Optional[Dict[str, float]] = None
    if args.state:
        state_vector = load_json_file(args.state)

    context: Optional[Dict[str, Any]] = None
    if args.context:
        context = load_json_file(args.context)

    outputs_history: Optional[List[str]] = None
    if args.history:
        outputs_history = load_json_file(args.history)

    # Generate oracle
    try:
        output = generate_oracle(
            state_vector=state_vector,
            context=context,
            requested_depth=args.depth,
            anchor=args.anchor,
            outputs_history=outputs_history
        )

        # Print output
        if args.pretty:
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(output, ensure_ascii=False))

        # Optionally show drift log
        if args.show_drift_log:
            from abraxas.oracle.drift import DRIFT_LOG_PATH
            if DRIFT_LOG_PATH.exists():
                print("\n--- Last 5 Drift Log Entries ---", file=sys.stderr)
                lines = DRIFT_LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
                for line in lines[-5:]:
                    entry = json.loads(line)
                    print(
                        f"[{entry['utc']}] {entry['status'].upper()} | "
                        f"drift={entry['drift_magnitude']:.3f} | "
                        f"gate={entry['gate_state']}",
                        file=sys.stderr
                    )

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
