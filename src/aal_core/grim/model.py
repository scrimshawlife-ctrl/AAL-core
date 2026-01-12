"""GRIM catalog data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


MAX_CHANGELOG_ENTRIES = 200


def _sorted_unique(values: Iterable[str]) -> List[str]:
    return sorted({v for v in values if v})


def _edge_key(edge: "RuneEdge") -> Tuple[str, str, str]:
    return (edge.src_id, edge.dst_id, edge.kind)


def _provenance_key(prov: Dict[str, Any]) -> Tuple[str, str]:
    return (str(prov.get("path", "")), str(prov.get("overlay", "")))


@dataclass
class RuneEdge:
    src_id: str
    dst_id: str
    kind: str = "link"

    def to_dict(self) -> Dict[str, str]:
        return {"src_id": self.src_id, "dst_id": self.dst_id, "kind": self.kind}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RuneEdge":
        return RuneEdge(
            src_id=str(data.get("src_id") or ""),
            dst_id=str(data.get("dst_id") or ""),
            kind=str(data.get("kind") or "link"),
        )


@dataclass
class RuneRecord:
    rune_id: str
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    edges_out: List[RuneEdge] = field(default_factory=list)
    governance_status: str = "active"
    provenance: List[Dict[str, Any]] = field(default_factory=list)

    def normalized(self) -> "RuneRecord":
        self.capabilities = _sorted_unique(self.capabilities)
        self.tags = _sorted_unique(self.tags)
        self.edges_out = sorted(self.edges_out, key=_edge_key)
        self.provenance = sorted(self.provenance, key=_provenance_key)
        return self

    def to_dict(self) -> Dict[str, Any]:
        self.normalized()
        data: Dict[str, Any] = {
            "rune_id": self.rune_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "edges_out": [edge.to_dict() for edge in self.edges_out],
            "governance_status": self.governance_status,
            "provenance": self.provenance,
        }
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RuneRecord":
        edges = [RuneEdge.from_dict(e) for e in data.get("edges_out", [])]
        return RuneRecord(
            rune_id=str(data.get("rune_id") or ""),
            name=str(data.get("name") or ""),
            version=data.get("version"),
            description=data.get("description"),
            capabilities=list(data.get("capabilities", []) or []),
            tags=list(data.get("tags", []) or []),
            edges_out=edges,
            governance_status=str(data.get("governance_status") or "active"),
            provenance=list(data.get("provenance", []) or []),
        ).normalized()


@dataclass
class GrimCatalog:
    runes: Dict[str, RuneRecord] = field(default_factory=dict)
    changelog: List[Dict[str, Any]] = field(default_factory=list)

    def upsert(self, record: RuneRecord, source: str = "scan") -> RuneRecord:
        existing = self.runes.get(record.rune_id)
        if existing:
            merged = self._merge_records(existing, record)
        else:
            merged = record
        merged.normalized()
        self.runes[record.rune_id] = merged
        self._append_changelog(record.rune_id, source, bool(existing))
        return merged

    def _merge_records(self, existing: RuneRecord, incoming: RuneRecord) -> RuneRecord:
        governance_status = existing.governance_status or incoming.governance_status
        name = existing.name or incoming.name
        version = existing.version or incoming.version
        description = existing.description or incoming.description
        capabilities = _sorted_unique(existing.capabilities + incoming.capabilities)
        tags = _sorted_unique(existing.tags + incoming.tags)
        edges = _merge_edges(existing.edges_out, incoming.edges_out)
        provenance = _merge_provenance(existing.provenance, incoming.provenance)
        return RuneRecord(
            rune_id=existing.rune_id,
            name=name,
            version=version,
            description=description,
            capabilities=capabilities,
            tags=tags,
            edges_out=edges,
            governance_status=governance_status,
            provenance=provenance,
        )

    def _append_changelog(self, rune_id: str, source: str, existed: bool) -> None:
        entry = {"rune_id": rune_id, "source": source, "event": "update" if existed else "create"}
        self.changelog.append(entry)
        if len(self.changelog) > MAX_CHANGELOG_ENTRIES:
            self.changelog = self.changelog[-MAX_CHANGELOG_ENTRIES :]

    def to_dict(self) -> Dict[str, Any]:
        runes_sorted = [self.runes[rid].to_dict() for rid in sorted(self.runes)]
        return {"runes": runes_sorted, "changelog": list(self.changelog)}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GrimCatalog":
        runes = {r["rune_id"]: RuneRecord.from_dict(r) for r in data.get("runes", [])}
        changelog = list(data.get("changelog", []) or [])
        return GrimCatalog(runes=runes, changelog=changelog)


def _merge_edges(existing: Sequence[RuneEdge], incoming: Sequence[RuneEdge]) -> List[RuneEdge]:
    by_key = {(_edge_key(e)): e for e in existing}
    for edge in incoming:
        by_key.setdefault(_edge_key(edge), edge)
    return sorted(by_key.values(), key=_edge_key)


def _merge_provenance(
    existing: Sequence[Dict[str, Any]], incoming: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    by_key = {_provenance_key(p): p for p in existing}
    for prov in incoming:
        by_key.setdefault(_provenance_key(prov), prov)
    return [by_key[key] for key in sorted(by_key)]
