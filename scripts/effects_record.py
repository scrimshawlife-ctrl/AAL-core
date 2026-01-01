from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from aal_core.ers.effects_store import load_effects, record_effect, save_effects


def load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Record observed knob effect deltas into EffectStore.")
    ap.add_argument("--module-id", required=True)
    ap.add_argument("--knob", required=True)
    ap.add_argument("--value", required=True)
    ap.add_argument("--before-metrics", required=True)
    ap.add_argument("--after-metrics", required=True)
    ap.add_argument("--store", default=".aal/effects_store.json")
    args = ap.parse_args()

    store = load_effects(Path(args.store))
    before = load_json(Path(args.before_metrics))
    after = load_json(Path(args.after_metrics))
    record_effect(
        store,
        module_id=args.module_id,
        knob=args.knob,
        value=args.value,
        before_metrics=before,
        after_metrics=after,
    )
    save_effects(store, Path(args.store))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

