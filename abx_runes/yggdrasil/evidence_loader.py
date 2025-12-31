from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from .evidence_bundle import minimal_validate, verify_hash
from .inputs_bundle import InputBundle
from .linkgen import evidence_port_name
from .schema import YggdrasilManifest


@dataclass(frozen=True)
class EvidenceLoadResult:
    """
    Deterministic evidence loader output:
    - bundle_paths_ok: verified evidence bundle files
    - bundle_paths_bad: list of {"path":..., "reason":...}
    - input_bundle: ports to add to planning bundle
    """
    bundle_paths_ok: Tuple[str, ...]
    bundle_paths_bad: Tuple[Dict[str, str], ...]
    input_bundle: InputBundle


def load_evidence_bundles(paths: List[str]) -> EvidenceLoadResult:
    """
    Load and verify evidence bundles from file paths.
    Returns ports to add to planning InputBundle (present iff at least one verified bundle).
    """
    ok: List[str] = []
    bad: List[Dict[str, str]] = []

    for pstr in sorted(set(paths)):
        p = Path(pstr)
        if not p.exists() or not p.is_file():
            bad.append({"path": pstr, "reason": "missing"})
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            bad.append({"path": pstr, "reason": "invalid_json"})
            continue
        try:
            minimal_validate(d)
        except Exception:
            bad.append({"path": pstr, "reason": "contract_invalid"})
            continue
        if not verify_hash(d):
            bad.append({"path": pstr, "reason": "hash_mismatch"})
            continue
        ok.append(pstr)

    # Planner ports: per-bridge evidence ports emitted from verified bundles.
    present: Dict[str, str] = {}
    for pstr in ok:
        d = json.loads(Path(pstr).read_text(encoding="utf-8"))
        bridges = d.get("bridges", []) or []
        for b in bridges:
            frm = str(b.get("from", "")).strip()
            to = str(b.get("to", "")).strip()
            if not frm or not to:
                continue
            present[evidence_port_name(frm, to)] = "evidence_bundle"

    return EvidenceLoadResult(
        bundle_paths_ok=tuple(sorted(ok)),
        bundle_paths_bad=tuple(sorted(bad, key=lambda x: (x["reason"], x["path"]))),
        input_bundle=InputBundle(present=present),
    )


def load_evidence_bundles_for_manifest(paths: List[str], manifest: YggdrasilManifest) -> EvidenceLoadResult:
    """
    Like load_evidence_bundles, but only emits per-bridge evidence ports if the bridge exists in manifest.links.
    """
    base = load_evidence_bundles(paths)
    if not base.bundle_paths_ok:
        return base

    valid_edges = {(l.from_node, l.to_node) for l in manifest.links}
    present: Dict[str, str] = {}
    bad = list(base.bundle_paths_bad)
    ok = list(base.bundle_paths_ok)

    for pstr in base.bundle_paths_ok:
        d = json.loads(Path(pstr).read_text(encoding="utf-8"))
        bridges = d.get("bridges", []) or []
        for b in bridges:
            frm = str(b.get("from", "")).strip()
            to = str(b.get("to", "")).strip()
            if not frm or not to:
                continue
            if (frm, to) not in valid_edges:
                bad.append({"path": pstr, "reason": f"bridge_not_in_manifest:{frm}->{to}"})
                continue
            present[evidence_port_name(frm, to)] = "evidence_bundle"

    return EvidenceLoadResult(
        bundle_paths_ok=tuple(sorted(ok)),
        bundle_paths_bad=tuple(sorted(bad, key=lambda x: (x["reason"], x["path"]))),
        input_bundle=InputBundle(present=present),
    )
