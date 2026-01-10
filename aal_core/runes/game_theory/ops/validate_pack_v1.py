from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any, List


CORPUS_REQUIRED = {"id", "kind", "title", "payload", "links", "tags", "provenance"}
VECTOR_REQUIRED = {"schema_version", "vector_id", "game", "expected", "notes", "provenance"}
GAME_REQUIRED = {"players", "strategies", "payoffs", "type"}
EXPECTED_REQUIRED = {"equilibria", "dominant_strategies"}


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _validate_corpus_item(item: Dict[str, Any], path: Path) -> None:
    missing = CORPUS_REQUIRED - item.keys()
    if missing:
        raise ValueError(f"Corpus item missing fields {missing} in {path}")
    if item["kind"] not in {"concept", "game", "pitfall", "glossary"}:
        raise ValueError(f"Unsupported kind {item['kind']} in {path}")


def _validate_vector_item(item: Dict[str, Any], path: Path) -> None:
    missing = VECTOR_REQUIRED - item.keys()
    if missing:
        raise ValueError(f"Vector item missing fields {missing} in {path}")
    if item["schema_version"] != "aal.gametheory.vector.v1":
        raise ValueError(f"Unexpected schema_version {item['schema_version']} in {path}")
    game = item["game"]
    missing_game = GAME_REQUIRED - game.keys()
    if missing_game:
        raise ValueError(f"Vector game missing fields {missing_game} in {path}")
    expected = item["expected"]
    missing_expected = EXPECTED_REQUIRED - expected.keys()
    if missing_expected:
        raise ValueError(f"Vector expected missing fields {missing_expected} in {path}")
    players = game["players"]
    strategies = game["strategies"]
    payoffs = game["payoffs"]
    if players != len(strategies):
        raise ValueError(f"Players/strategies mismatch in {path}")
    if len(payoffs) != len(strategies):
        raise ValueError(f"Payoff rows mismatch in {path}")


def validate_pack(corpus_dir: Path, vectors_dir: Path) -> None:
    corpus_files = sorted(p for p in corpus_dir.glob("*.jsonl") if p.is_file())
    vector_files = sorted(p for p in vectors_dir.glob("*.jsonl") if p.is_file())
    if not corpus_files:
        raise FileNotFoundError(f"No corpus files found in {corpus_dir}")
    if not vector_files:
        raise FileNotFoundError(f"No vector files found in {vectors_dir}")

    for path in corpus_files:
        for item in _read_jsonl(path):
            _validate_corpus_item(item, path)

    for path in vector_files:
        for item in _read_jsonl(path):
            _validate_vector_item(item, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the game theory training pack.")
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--vectors-dir", type=Path, required=True)
    args = parser.parse_args()
    validate_pack(args.corpus_dir, args.vectors_dir)


if __name__ == "__main__":
    main()
