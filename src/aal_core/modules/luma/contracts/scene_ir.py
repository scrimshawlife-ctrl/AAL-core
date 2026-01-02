from dataclasses import dataclass
from typing import Any, Dict, List
import hashlib
import json


@dataclass(frozen=True)
class LumaEntity:
    entity_id: str
    entity_type: str  # motif | domain | subdomain | event
    attributes: Dict[str, Any]


@dataclass(frozen=True)
class LumaEdge:
    source: str
    target: str
    edge_type: str  # resonance | synch | transfer | shadow
    weight: float
    attributes: Dict[str, Any]


@dataclass(frozen=True)
class LumaPatternInstance:
    pattern_id: str
    parameters: Dict[str, Any]
    entities: List[str]  # entity_ids
    edges: List[int]  # indices into edges list


@dataclass(frozen=True)
class LumaSceneIR:
    scene_id: str
    seed: int
    provenance: Dict[str, Any]
    entities: List[LumaEntity]
    edges: List[LumaEdge]
    patterns: List[LumaPatternInstance]
    semantic_map: Dict[str, str]
    constraints: Dict[str, Any]

    def _canonical_payload(self) -> Dict[str, Any]:
        ents = sorted(
            [e.__dict__ for e in self.entities],
            key=lambda d: (d["entity_type"], d["entity_id"]),
        )
        eds = sorted(
            [e.__dict__ for e in self.edges],
            key=lambda d: (d["edge_type"], d["source"], d["target"], float(d["weight"])),
        )
        pats = sorted(
            [p.__dict__ for p in self.patterns],
            key=lambda d: (
                d["pattern_id"],
                json.dumps(d.get("parameters", {}), sort_keys=True),
            ),
        )
        return {
            "scene_id": self.scene_id,
            "seed": int(self.seed),
            "provenance": self.provenance,
            "entities": ents,
            "edges": eds,
            "patterns": pats,
            "semantic_map": dict(sorted(self.semantic_map.items(), key=lambda kv: kv[0])),
            "constraints": dict(sorted(self.constraints.items(), key=lambda kv: kv[0])),
        }

    def stable_hash(self) -> str:
        payload = json.dumps(self._canonical_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
