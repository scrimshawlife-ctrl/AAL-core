from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Mapping

from ..contracts.enums import NotComputable
from ..contracts.provenance import sha256_hex
from ..contracts.scene_ir import LumaSceneIR

NC = NotComputable.VALUE.value


@dataclass(frozen=True)
class LayoutPoint:
    x: float
    y: float


def stable_layout_points(scene: LumaSceneIR) -> Mapping[str, LayoutPoint]:
    """
    Deterministic layout derived from scene hash + seed.

    Note: layout is renderer-level (how it looks), not part of scene semantics.
    """

    if isinstance(scene.entities, str):
        return {}

    ids = tuple(sorted((e.entity_id for e in scene.entities)))
    n = max(1, len(ids))
    rng = random.Random(scene.seed ^ int(scene.hash[:8], 16))
    rot = rng.random() * 2.0 * math.pi
    r = 120.0

    pts: Dict[str, LayoutPoint] = {}
    for i, eid in enumerate(ids):
        theta = rot + (2.0 * math.pi * i / n)
        # small deterministic jitter avoids perfect overlap without nondeterminism
        jx = (rng.random() - 0.5) * 6.0
        jy = (rng.random() - 0.5) * 6.0
        pts[eid] = LayoutPoint(x=r * math.cos(theta) + jx, y=r * math.sin(theta) + jy)
    return pts


def domain_color(domain: str) -> str:
    """
    Stable domain->color mapping (SVG hex).
    """

    if not domain or domain == NC:
        return "#777777"
    h = sha256_hex({"domain": domain})
    # Use first 6 hex digits but keep it readable (avoid too-dark)
    r = 64 + int(h[0:2], 16) // 2
    g = 64 + int(h[2:4], 16) // 2
    b = 64 + int(h[4:6], 16) // 2
    return f"#{r:02x}{g:02x}{b:02x}"


def thickness_from_magnitude(m: float) -> float:
    # Canonical: edge thickness expresses resonance magnitude.
    return 1.0 + min(6.0, max(0.0, float(m)) ** 0.5)


def alpha_from_uncertainty(u: float) -> float:
    # Canonical: transparency expresses uncertainty (higher uncertainty -> more transparent).
    uu = min(1.0, max(0.0, float(u)))
    return 1.0 - 0.75 * uu
