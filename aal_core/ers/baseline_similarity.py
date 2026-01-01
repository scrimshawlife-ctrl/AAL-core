from __future__ import annotations

from typing import Dict, Set


def similarity(a: Dict[str, str], b: Dict[str, str]) -> float:
    """
    Deterministic similarity for categorical baseline buckets.

    Scoring per dimension (only for keys present in BOTH dicts):
    - Exact match -> 1.0
    - Adjacent bucket -> 0.5 (string heuristic: same first token)
    - Different -> 0.0

    Final similarity is the mean across shared dimensions.
    """
    if not a or not b:
        return 0.0

    keys: Set[str] = set(a) & set(b)
    if not keys:
        return 0.0

    score = 0.0
    for k in sorted(keys):
        av = a[k]
        bv = b[k]
        if av == bv:
            score += 1.0
            continue

        # adjacency heuristic: same leading token (e.g., "<= 10" vs "<= 50")
        pa = str(av).split()[0] if str(av).split() else str(av)
        pb = str(bv).split()[0] if str(bv).split() else str(bv)
        score += 0.5 if pa == pb else 0.0

    return score / float(len(keys))

