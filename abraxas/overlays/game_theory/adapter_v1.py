from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json


def attach_game_theory_digest(oracle_packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds a compact training digest so Abraxas can:
      - reference game-theory structures without overfitting narrative
      - flag when interactions look game-like but are under-specified
    """
    base = Path("aal_core/runes/game_theory/corpus/concepts.v1.jsonl")
    if not base.exists():
        return oracle_packet

    concepts: List[Dict[str, Any]] = []
    with base.open("r", encoding="utf-8") as handle:
        for i, line in enumerate(handle):
            if i >= 6:
                break
            concepts.append(json.loads(line))

    oracle_packet.setdefault("attachments", {})["game_theory_digest_v1"] = {
        "schema_version": "abraxas.game_theory.digest.v1",
        "concepts": [
            {"title": concept["title"], "def": concept["payload"]["definition"]}
            for concept in concepts
        ],
        "guardrails": [
            "If payoffs/info are unknown → label non-computable.",
            "Equilibrium is a hypothesis in non-stationary regimes.",
            "Prefer risk-dominance language when uncertainty is high.",
        ],
    }
    return oracle_packet
