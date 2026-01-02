from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import hashlib
import json
import math

from ..contracts.auto_view_ir import AutoViewPlan
from ..contracts.enums import NotComputable
from ..contracts.scene_ir import LumaSceneIR

NC = NotComputable.VALUE.value


@dataclass(frozen=True)
class AutoLensConfig:
    max_nodes: int = 32
    max_labels: int = 28
    max_primitives: int = 3
    sankey_max_pairs: int = 8
    min_confidence: float = 0.35


def _clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def _stable_id(scene_hash: str, view_id: str, payload: Dict[str, Any]) -> str:
    src = json.dumps(
        {"scene_hash": scene_hash, "view_id": view_id, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]


def _introspect(scene: LumaSceneIR) -> Dict[str, Any]:
    ents = () if isinstance(scene.entities, str) else scene.entities
    edges = () if isinstance(scene.edges, str) else scene.edges

    counts: Dict[str, int] = {}
    for e in ents:
        counts[e.kind] = counts.get(e.kind, 0) + 1

    edge_counts: Dict[str, int] = {}
    for ed in edges:
        edge_counts[ed.kind] = edge_counts.get(ed.kind, 0) + 1

    motifs = [e for e in ents if e.kind == "motif"]
    domains = [e for e in ents if e.kind == "domain"]
    events = [e for e in ents if e.kind == "event"]

    motif_has_domain = sum(1 for m in motifs if isinstance(m.domain, str) and m.domain != NC)
    motif_has_salience = sum(
        1 for m in motifs if isinstance(m.metrics.get("salience"), (int, float))
    )
    event_has_ts = sum(
        1 for ev in events if isinstance(ev.metrics.get("timestamp"), str)
    )

    transfer_edges = [ed for ed in edges if ed.kind == "transfer"]
    pairs = set((ed.source_id, ed.target_id) for ed in transfer_edges)

    return {
        "entity_counts": counts,
        "edge_counts": edge_counts,
        "motif_has_domain": motif_has_domain,
        "motif_has_salience": motif_has_salience,
        "event_has_ts": event_has_ts,
        "transfer_pair_count": len(pairs),
        "transfer_pairs": sorted(list(pairs)),
        "has_domains": len(domains) > 0,
        "has_motifs": len(motifs) > 0,
        "has_events": len(events) > 0,
        "has_transfers": len(transfer_edges) > 0,
    }


def _score_candidate(
    intro: Dict[str, Any],
    primitives: List[str],
    coverage: float,
    complexity: float,
    redundancy: float,
) -> Dict[str, float]:
    readability = _clamp(1.0 - complexity)
    info_gain = _clamp(coverage * readability * (1.0 - redundancy))
    confidence = _clamp(0.2 + 0.55 * coverage + 0.35 * readability - 0.15 * redundancy)
    return {
        "coverage": float(_clamp(coverage)),
        "readability": float(readability),
        "redundancy": float(_clamp(redundancy)),
        "info_gain": float(info_gain),
        "confidence": float(confidence),
    }


def _candidate_graph(
    scene: LumaSceneIR, intro: Dict[str, Any], cfg: AutoLensConfig
) -> Dict[str, Any]:
    motifs = sorted(
        [e for e in scene.entities if e.kind == "motif"], key=lambda e: e.entity_id
    )
    edges = [ed for ed in scene.edges if ed.kind in ("resonance", "synch", "transfer")]
    edges = sorted(edges, key=lambda ed: (ed.kind, ed.source_id, ed.target_id))

    motifs = motifs[: cfg.max_nodes]
    motif_ids = [m.entity_id for m in motifs]
    motif_set = set(motif_ids)
    edges = [ed for ed in edges if ed.source_id in motif_set and ed.target_id in motif_set]

    n = max(1, len(motif_ids))
    layout_nodes = []
    for i, mid in enumerate(motif_ids):
        theta = (2 * math.pi * i) / n
        layout_nodes.append({"id": mid, "theta": theta})

    layout_edges = [
        {
            "source": ed.source_id,
            "target": ed.target_id,
            "edge_type": ed.kind,
            "weight": float(ed.resonance_magnitude)
            if isinstance(ed.resonance_magnitude, (int, float))
            else 0.0,
        }
        for ed in edges
    ]

    coverage = _clamp(
        (len(motif_ids) / max(1, intro["entity_counts"].get("motif", 0))) * 0.7
        + (1.0 if len(layout_edges) > 0 else 0.2) * 0.3
    )
    complexity = _clamp(0.35 + 0.008 * len(motif_ids) + 0.004 * len(layout_edges))
    redundancy = 0.25 if intro.get("has_domains") else 0.10

    return {
        "view_id": "auto.graph_v0",
        "primitives": ["nodes", "edges"],
        "layout": {"nodes": layout_nodes, "edges": layout_edges, "layout_kind": "circle"},
        "channels": {
            "node_size": "entity.metrics.salience",
            "edge_thickness": "edge.resonance_magnitude",
        },
        "mappings": [
            {"source": "entity.kind", "target": "nodes"},
            {"source": "edge.kind", "target": "edges.edge_type"},
            {"source": "edge.resonance_magnitude", "target": "edges.weight"},
        ],
        "scores": _score_candidate(intro, ["nodes", "edges"], coverage, complexity, redundancy),
        "warnings": [],
    }


def _candidate_matrix(
    scene: LumaSceneIR, intro: Dict[str, Any], cfg: AutoLensConfig
) -> Dict[str, Any]:
    domains = sorted(
        [e for e in scene.entities if e.kind == "domain"], key=lambda e: e.entity_id
    )
    motifs = sorted(
        [e for e in scene.entities if e.kind == "motif"],
        key=lambda e: (
            -float(e.metrics.get("salience", 0.0))
            if isinstance(e.metrics.get("salience"), (int, float))
            else 0.0,
            e.entity_id,
        ),
    )

    domains = domains[: min(len(domains), 16)]
    motifs = motifs[: cfg.max_nodes]

    dom_ids = [d.entity_id for d in domains]
    mot_ids = [m.entity_id for m in motifs]
    dom_set = set(dom_ids)

    cells: Dict[str, Dict[str, float]] = {}
    vmax = 0.0
    mapped = 0
    for m in motifs:
        mid = m.entity_id
        dom = m.domain
        sal = float(m.metrics.get("salience", 0.0)) if isinstance(
            m.metrics.get("salience"), (int, float)
        ) else 0.0
        row = {}
        for d in dom_ids:
            v = sal if (isinstance(dom, str) and dom == d) else 0.0
            row[d] = v
            vmax = max(vmax, v)
        cells[mid] = row
        if isinstance(dom, str) and dom in dom_set:
            mapped += 1

    vmax = vmax if vmax > 0 else 1.0

    coverage = _clamp(
        (mapped / max(1, len(motifs))) * 0.8
        + (len(dom_ids) / max(1, intro["entity_counts"].get("domain", 0))) * 0.2
    )
    complexity = _clamp(0.25 + 0.01 * len(mot_ids) + 0.008 * len(dom_ids))
    redundancy = 0.12

    warnings = []
    if mapped == 0:
        warnings.append("No motif.domain mappings found; matrix may be empty.")
    if intro.get("motif_has_salience", 0) == 0:
        warnings.append("No salience field found; cell values may be uniform/zero.")

    return {
        "view_id": "auto.matrix_v0",
        "primitives": ["matrix", "heatmap"],
        "layout": {
            "rows": mot_ids,
            "cols": dom_ids,
            "cells": cells,
            "value_max": vmax,
            "layout_kind": "incidence",
        },
        "channels": {"cell_opacity": "entity.metrics.salience"},
        "mappings": [
            {"source": "entity.domain", "target": "matrix.col"},
            {"source": "entity.metrics.salience", "target": "heatmap.value"},
        ],
        "scores": _score_candidate(
            intro, ["matrix", "heatmap"], coverage, complexity, redundancy
        ),
        "warnings": warnings,
    }


def _candidate_flow(
    scene: LumaSceneIR, intro: Dict[str, Any], cfg: AutoLensConfig
) -> Dict[str, Any]:
    domains = sorted(
        [e for e in scene.entities if e.kind == "domain"], key=lambda e: e.entity_id
    )
    dom_ids = [d.entity_id for d in domains]
    dom_set = set(dom_ids)

    transfers = [ed for ed in scene.edges if ed.kind == "transfer"]
    pairs: Dict[Tuple[str, str], float] = {}
    for ed in transfers:
        src = ed.source_id
        tgt = ed.target_id
        if src in dom_set and tgt in dom_set:
            w = float(ed.resonance_magnitude) if isinstance(
                ed.resonance_magnitude, (int, float)
            ) else 0.0
            pairs[(src, tgt)] = pairs.get((src, tgt), 0.0) + w

    pair_count = len(pairs)
    preferred = "sankey" if pair_count <= cfg.sankey_max_pairs else "chord"

    flows = [
        {"source_domain": a, "target_domain": b, "weight": float(w)}
        for (a, b), w in sorted(pairs.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    ]
    vmax = max([f["weight"] for f in flows], default=1.0)

    coverage = _clamp(
        (pair_count / max(1, intro.get("transfer_pair_count", 0))) * 0.6
        + (1.0 if pair_count > 0 else 0.0) * 0.4
    )
    complexity = _clamp(0.28 + 0.02 * min(pair_count, 20))
    redundancy = 0.18

    warnings = []
    if pair_count == 0:
        warnings.append(
            "No valid transfer source/target pairs; flow view empty."
        )

    return {
        "view_id": "auto.flow_v0",
        "primitives": ["flows"],
        "layout": {
            "domains": dom_ids,
            "flows": flows,
            "weight_max": vmax,
            "preferred_flow_view": preferred,
            "pair_count": pair_count,
            "layout_kind": "domain_flow",
        },
        "channels": {
            "flow_thickness": "edge.resonance_magnitude",
            "flow_opacity": "edge.resonance_magnitude",
        },
        "mappings": [
            {"source": "edge.source_id", "target": "flows.source_domain"},
            {"source": "edge.target_id", "target": "flows.target_domain"},
            {"source": "edge.resonance_magnitude", "target": "flows.weight"},
        ],
        "scores": _score_candidate(intro, ["flows"], coverage, complexity, redundancy),
        "warnings": warnings,
    }


def _candidate_timeline(
    scene: LumaSceneIR, intro: Dict[str, Any], cfg: AutoLensConfig
) -> Dict[str, Any]:
    events = sorted(
        [e for e in scene.entities if e.kind == "event"], key=lambda e: e.entity_id
    )
    ev = []
    for e in events:
        ts = e.metrics.get("timestamp")
        if isinstance(ts, str):
            ev.append(
                {
                    "id": e.entity_id,
                    "timestamp": ts,
                    "motifs": list(e.metrics.get("motifs", []))
                    if isinstance(e.metrics.get("motifs"), list)
                    else [],
                }
            )
    ev = ev[: min(len(ev), 64)]

    coverage = _clamp(
        (len(ev) / max(1, intro["entity_counts"].get("event", 0)))
        if intro["entity_counts"].get("event", 0)
        else 0.0
    )
    complexity = _clamp(0.22 + 0.01 * min(len(ev), 64))
    redundancy = 0.22 if intro.get("has_transfers") else 0.10

    warnings = []
    if len(ev) == 0:
        warnings.append("No timestamped events found; timeline view empty.")

    return {
        "view_id": "auto.timeline_v0",
        "primitives": ["timeline", "nodes", "edges"],
        "layout": {"events": ev, "layout_kind": "timeline_events"},
        "channels": {"event_opacity": "entity.metrics.salience"},
        "mappings": [
            {"source": "time_axis.steps", "target": "timeline.x"},
        ],
        "scores": _score_candidate(
            intro, ["timeline", "nodes", "edges"], coverage, complexity, redundancy
        ),
        "warnings": warnings,
    }


class AutoLens:
    lens_id = "luma.auto_lens"
    lens_version = "0.1.0"

    def plan(self, scene: LumaSceneIR, cfg: AutoLensConfig | None = None) -> AutoViewPlan:
        cfg = cfg or AutoLensConfig()
        scene_hash = scene.hash
        intro = _introspect(scene)

        candidates: List[Dict[str, Any]] = []
        if intro.get("has_motifs"):
            candidates.append(_candidate_graph(scene, intro, cfg))
        if intro.get("has_domains") and intro.get("motif_has_domain", 0) > 0:
            candidates.append(_candidate_matrix(scene, intro, cfg))
        if intro.get("has_domains") and intro.get("has_transfers"):
            candidates.append(_candidate_flow(scene, intro, cfg))
        if intro.get("has_events") and intro.get("event_has_ts", 0) > 0:
            candidates.append(_candidate_timeline(scene, intro, cfg))

        candidates.sort(
            key=lambda c: (
                -float(c["scores"]["confidence"]),
                -float(c["scores"]["info_gain"]),
                c["view_id"],
            )
        )

        chosen = candidates[0] if candidates else None
        warnings = []
        if not chosen:
            chosen = {
                "view_id": "auto.empty_v0",
                "primitives": [],
                "layout": {"layout_kind": "empty"},
                "channels": {},
                "mappings": [],
                "scores": {
                    "coverage": 0.0,
                    "readability": 1.0,
                    "redundancy": 0.0,
                    "info_gain": 0.0,
                    "confidence": 0.0,
                },
                "warnings": ["No viable lens candidates from given SceneIR."],
            }

        if float(chosen["scores"]["confidence"]) < cfg.min_confidence:
            warnings.append(
                "Low confidence auto-view selection "
                f"({chosen['scores']['confidence']:.2f}); data may be sparse/ambiguous."
            )
        warnings.extend(list(chosen.get("warnings", [])))

        payload = {
            "view_id": chosen["view_id"],
            "primitives": chosen["primitives"],
            "layout": chosen["layout"],
            "channels": chosen["channels"],
            "mappings": chosen["mappings"],
            "scores": chosen["scores"],
        }
        plan_id = _stable_id(scene_hash, chosen["view_id"], payload)

        return AutoViewPlan(
            schema="AutoViewPlan.v0",
            scene_hash=scene_hash,
            view_id=chosen["view_id"],
            primitives=list(chosen["primitives"])[: cfg.max_primitives],
            layout=chosen["layout"],
            channels=chosen["channels"],
            mappings=chosen["mappings"],
            scores=chosen["scores"],
            reasons={
                "introspection": intro,
                "selection": {
                    "ranked": [
                        {"view_id": c["view_id"], "scores": c["scores"]}
                        for c in candidates[:6]
                    ],
                    "chosen": chosen["view_id"],
                    "plan_id": plan_id,
                },
            },
            warnings=warnings,
            provenance={
                "scene_hash": scene_hash,
                "source_frame_provenance": scene.to_canonical_dict(True)[
                    "source_frame_provenance"
                ],
                "lens": {"id": self.lens_id, "version": self.lens_version},
                "config": cfg.__dict__,
            },
            limits=cfg.__dict__,
        )
