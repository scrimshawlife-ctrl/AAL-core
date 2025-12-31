from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .schema import (
    Lane,
    NodeKind,
    PromotionState,
    ProvenanceSpec,
    Realm,
    YggdrasilManifest,
    YggdrasilNode,
)
from .hashing import canonical_json_dumps
from .io import recompute_and_lock_hash
from .overlay_introspect import load_overlay_manifest_json, extract_declared_runes
from .linkgen import ensure_links_for_crossings
from .lint import render_forbidden_crossings_report


@dataclass(frozen=True)
class RealEmitterConfig:
    """
    Deterministic discovery config.
    """
    repo_root: Path
    overlays_dir: Path = Path(".aal/overlays")
    classify_overrides_path: Path = Path("yggdrasil.classify.json")


def emit_manifest_from_repo(cfg: RealEmitterConfig, prov: ProvenanceSpec) -> Dict:
    """
    Emit a JSON-ready manifest dict from repository structure.

    Sources:
    - .aal/overlays/* (overlay presence as nodes)
    - optional yggdrasil.classify.json (realm/lane overrides)
    """
    root = cfg.repo_root
    overlays_path = (root / cfg.overlays_dir)
    overrides_path = (root / cfg.classify_overrides_path)

    overrides = _load_overrides(overrides_path)
    overlay_names = _discover_overlay_names(overlays_path)

    nodes: List[Dict] = []
    overlay_manifest_errors: List[Dict] = []

    # Governance spine
    nodes.append(_node_dict(
        id="root.seed",
        kind=NodeKind.ROOT_POLICY,
        realm=Realm.MIDGARD,
        lane=Lane.NEUTRAL,
        authority_level=100,
        parent=None,
        depends_on=(),
        promotion_state=PromotionState.PROMOTED,
    ))
    nodes.append(_node_dict(
        id="kernel.registry",
        kind=NodeKind.KERNEL,
        realm=Realm.MIDGARD,
        lane=Lane.NEUTRAL,
        authority_level=90,
        parent="root.seed",
        depends_on=("root.seed",),
        promotion_state=PromotionState.PROMOTED,
    ))

    # Realm scaffolding (pure metadata; safe defaults)
    # Note: realm nodes have NO depends_on to avoid cross-realm validation issues
    # They exist in tree hierarchy (parent) only, not data dependency graph
    nodes.append(_node_dict(
        id="realm.midgard",
        kind=NodeKind.REALM,
        realm=Realm.MIDGARD,
        lane=Lane.NEUTRAL,
        authority_level=80,
        parent="kernel.registry",
        depends_on=(),
        promotion_state=PromotionState.PROMOTED,
    ))
    nodes.append(_node_dict(
        id="realm.hel",
        kind=NodeKind.REALM,
        realm=Realm.HEL,
        lane=Lane.SHADOW,
        authority_level=80,
        parent="kernel.registry",
        depends_on=(),
        promotion_state=PromotionState.PROMOTED,
    ))
    nodes.append(_node_dict(
        id="realm.asgard",
        kind=NodeKind.REALM,
        realm=Realm.ASGARD,
        lane=Lane.FORECAST,
        authority_level=80,
        parent="kernel.registry",
        depends_on=(),
        promotion_state=PromotionState.PROMOTED,
    ))

    # Overlay nodes + optional rune nodes (declared via overlay manifest JSON)
    for name in overlay_names:
        oid = f"overlay.{name}"
        overlay_dir = overlays_path / name

        # overlay classification (safe default)
        realm, lane = _apply_override(oid, overrides, default_realm=Realm.MIDGARD, default_lane=Lane.NEUTRAL)
        nodes.append(_node_dict(
            id=oid,
            kind=NodeKind.KERNEL,
            realm=realm,
            lane=lane,
            authority_level=70,
            parent="realm.midgard",
            depends_on=("kernel.registry", "realm.midgard"),
            promotion_state=PromotionState.CANDIDATE,
        ))

        # declared runes (only if explicitly declared by JSON)
        om = load_overlay_manifest_json(overlay_dir)
        if om is None:
            # Could be missing OR invalid schema. Record deterministically.
            # We do not attempt to distinguish to avoid nondeterminism from exception text.
            overlay_manifest_errors.append({"overlay": name, "reason": "missing_or_invalid_overlay_manifest"})
            continue

        declared = extract_declared_runes(om)
        for d in declared:
            # rune node id is declared id; parent is overlay shell
            rid = d.rune_id
            r_override = overrides.get(rid, {})

            # Default rune realm/lane inherit from overlay unless overridden
            r_realm, r_lane = _apply_override(
                rid,
                overrides,
                default_realm=realm,
                default_lane=lane,
            )

            # Rune depends on overlay shell plus any declared deps (later validated)
            deps = tuple(sorted(set((oid,)) | set(d.depends_on)))

            nodes.append(_node_dict(
                id=rid,
                kind=NodeKind.RUNE,
                realm=r_realm,
                lane=r_lane,
                authority_level=60,
                parent=oid,
                depends_on=deps,
                promotion_state=PromotionState(str(r_override.get("promotion_state", "candidate"))),
            ))

    # Build node index for link generation
    nodes_by_id = {n["id"]: n for n in nodes}

    # Auto-generate RuneLinks for cross-realm dependencies (safe auto-allow except shadow->forecast)
    links, forbidden = ensure_links_for_crossings(nodes_by_id=nodes_by_id, existing_links=[])

    # Attach a deterministic lint report into provenance (non-exec metadata)
    lint_report = render_forbidden_crossings_report(forbidden)

    manifest = {
        "provenance": {
            "schema_version": prov.schema_version,
            "manifest_hash": "",
            "created_at": prov.created_at,
            "updated_at": prov.updated_at,
            "source_commit": prov.source_commit,
            "lint": {
                "forbidden_crossings": forbidden,
                "overlay_manifest_errors": overlay_manifest_errors,
                "report": lint_report,
            },
        },
        "nodes": nodes,
        "links": links,
    }

    # lock provenance.manifest_hash deterministically
    manifest = recompute_and_lock_hash(manifest)
    return manifest


def _discover_overlay_names(overlays_path: Path) -> Tuple[str, ...]:
    if not overlays_path.exists() or not overlays_path.is_dir():
        return ()
    names: List[str] = []
    for p in overlays_path.iterdir():
        if p.is_dir() and not p.name.startswith("."):
            names.append(p.name)
    return tuple(sorted(set(names)))


def _load_overrides(path: Path) -> Dict:
    """
    Optional file:
    {
      "overlay.abraxas": {"realm":"ASGARD","lane":"forecast"}
    }
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Deterministic failure: treat as no overrides
        return {}


def _apply_override(node_id: str, overrides: Dict, default_realm: Realm, default_lane: Lane) -> Tuple[Realm, Lane]:
    o = overrides.get(node_id, {})
    r = str(o.get("realm", default_realm.value))
    l = str(o.get("lane", default_lane.value))
    try:
        return (Realm(r), Lane(l))
    except Exception:
        return (default_realm, default_lane)


def _node_dict(
    *,
    id: str,
    kind: NodeKind,
    realm: Realm,
    lane: Lane,
    authority_level: int,
    parent: Optional[str],
    depends_on: Iterable[str],
    promotion_state: PromotionState,
) -> Dict:
    return {
        "id": id,
        "kind": kind.value,
        "realm": realm.value,
        "lane": lane.value,
        "authority_level": int(authority_level),
        "parent": parent,
        "depends_on": list(depends_on),
        "promotion_state": promotion_state.value,
        "inputs": [],
        "outputs": [],
        "stabilization": {"window_cycles": 0, "min_cycles_before_promotion_considered": 0, "decay_constant": 0.0},
        "governance": {"rent_metrics": [], "gates_required": []},
    }
