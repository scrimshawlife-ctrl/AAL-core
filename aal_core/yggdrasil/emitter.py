from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass(frozen=True)
class EmitContext:
    """
    Minimal context. Extend later (but add-only) for registry access, versioning, etc.
    """
    schema_version: str
    created_at: str
    updated_at: str
    source_commit: str


class ManifestEmitter(Protocol):
    """
    Interface: produce a Yggdrasil manifest dict (JSON-ready).
    Keep it dict-based to avoid coupling to schema loader details.
    """
    def emit(self, ctx: EmitContext) -> Dict[str, Any]:
        ...


class StubEmitter:
    """
    Placeholder emitter that emits only a root + kernel node.
    Replace with a real registry-backed emitter later.
    """
    def emit(self, ctx: EmitContext) -> Dict[str, Any]:
        return {
            "provenance": {
                "schema_version": ctx.schema_version,
                "manifest_hash": "",
                "created_at": ctx.created_at,
                "updated_at": ctx.updated_at,
                "source_commit": ctx.source_commit,
            },
            "nodes": [
                {
                    "id": "root.seed",
                    "kind": "root_policy",
                    "realm": "MIDGARD",
                    "lane": "neutral",
                    "authority_level": 100,
                    "parent": None,
                    "depends_on": [],
                },
                {
                    "id": "kernel.registry",
                    "kind": "kernel",
                    "realm": "MIDGARD",
                    "lane": "neutral",
                    "authority_level": 90,
                    "parent": "root.seed",
                    "depends_on": ["root.seed"],
                },
            ],
            "links": [],
        }
