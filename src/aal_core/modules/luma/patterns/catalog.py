from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping, Tuple

from ..contracts.enums import PatternKind
from .base import BasePattern


@dataclass(frozen=True)
class PatternDescriptor:
    kind: PatternKind
    name: str
    summary: str
    input_contract: Mapping[str, Any]
    required_metrics: Tuple[str, ...]
    failure_modes: Tuple[str, ...]
    affordances: Tuple[str, ...]


def describe_patterns(patterns: Mapping[PatternKind, BasePattern]) -> Tuple[PatternDescriptor, ...]:
    out: List[PatternDescriptor] = []
    for kind in sorted(patterns.keys(), key=lambda k: k.value):
        p = patterns[kind]
        out.append(
            PatternDescriptor(
                kind=kind,
                name=kind.value,
                summary=(p.__doc__ or "").strip().splitlines()[0]
                if (p.__doc__ or "").strip()
                else "",
                input_contract=p.input_contract(),
                required_metrics=p.required_metrics(),
                failure_modes=p.failure_modes(),
                affordances=p.affordances(),
            )
        )
    return tuple(out)
