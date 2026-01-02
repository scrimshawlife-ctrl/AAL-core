from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class IdeationConstraints:
    """
    Governance constraints for proposing novel visualization grammars.

    Canonical rule: proposals are never defaults.
    """

    max_cognitive_load: float  # 0..1
    min_information_gain: float  # 0..1
    max_redundancy: float  # 0..1
    allow_new_primitives: bool  # must be False in v1
    require_semantic_justification: bool

    @staticmethod
    def v1_default() -> "IdeationConstraints":
        return IdeationConstraints(
            max_cognitive_load=0.55,
            min_information_gain=0.15,
            max_redundancy=0.65,
            allow_new_primitives=False,
            require_semantic_justification=True,
        )

    def as_dict(self) -> Mapping[str, object]:
        return {
            "max_cognitive_load": self.max_cognitive_load,
            "min_information_gain": self.min_information_gain,
            "max_redundancy": self.max_redundancy,
            "allow_new_primitives": self.allow_new_primitives,
            "require_semantic_justification": self.require_semantic_justification,
        }
