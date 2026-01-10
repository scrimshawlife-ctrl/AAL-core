from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict, Any


@dataclass(frozen=True)
class BuildInputs:
    corpus_dir: Path
    vectors_dir: Path
    output_dir: Path


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _list_jsonl_files(directory: Path) -> List[Path]:
    return sorted(p for p in directory.glob("*.jsonl") if p.is_file())


def _inputs_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\n")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def _generated_at() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is None:
        return "1970-01-01T00:00:00Z"
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _build_corpus_bundle(inputs: BuildInputs) -> Dict[str, Any]:
    corpus_files = _list_jsonl_files(inputs.corpus_dir)
    items: List[Dict[str, Any]] = []
    for path in corpus_files:
        items.extend(_read_jsonl(path))
    return {
        "schema_version": "aal.gametheory.corpus.v1",
        "generated_at_utc": _generated_at(),
        "inputs_hash": _inputs_hash(corpus_files),
        "items": items,
        "provenance": {
            "builder": "build_pack_v1",
            "files": [p.name for p in corpus_files],
        },
    }


def _build_vectors_bundle(inputs: BuildInputs) -> Dict[str, Any]:
    vector_files = _list_jsonl_files(inputs.vectors_dir)
    vectors: List[Dict[str, Any]] = []
    for path in vector_files:
        vectors.extend(_read_jsonl(path))
    return {
        "schema_version": "aal.gametheory.vectors.bundle.v1",
        "generated_at_utc": _generated_at(),
        "inputs_hash": _inputs_hash(vector_files),
        "vectors": vectors,
        "provenance": {
            "builder": "build_pack_v1",
            "files": [p.name for p in vector_files],
        },
    }


def build_pack(inputs: BuildInputs) -> None:
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    corpus_bundle = _build_corpus_bundle(inputs)
    vectors_bundle = _build_vectors_bundle(inputs)
    (inputs.output_dir / "corpus_bundle.v1.json").write_text(
        json.dumps(corpus_bundle, indent=2, sort_keys=True), encoding="utf-8"
    )
    (inputs.output_dir / "vectors_bundle.v1.json").write_text(
        json.dumps(vectors_bundle, indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the game theory training pack.")
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--vectors-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    inputs = BuildInputs(
        corpus_dir=args.corpus_dir,
        vectors_dir=args.vectors_dir,
        output_dir=args.output_dir,
    )
    build_pack(inputs)


if __name__ == "__main__":
    main()
