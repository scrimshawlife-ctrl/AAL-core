"""
Overlay manifest schema, validation, and persistence.

Manifests define overlay metadata, entrypoints, capabilities, and policies.
Stored as JSON at .aal/overlays/<overlay_name>/manifest.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class HTTPEntrypoint:
    """HTTP-based overlay entrypoint."""
    base_url: str

    def to_dict(self) -> Dict[str, str]:
        return {"base_url": self.base_url}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HTTPEntrypoint:
        if "base_url" not in data:
            raise ValueError("HTTPEntrypoint requires 'base_url'")
        return cls(base_url=data["base_url"])


@dataclass
class ProcEntrypoint:
    """Process-based overlay entrypoint."""
    command: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"command": self.command}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProcEntrypoint:
        if "command" not in data:
            raise ValueError("ProcEntrypoint requires 'command'")
        if not isinstance(data["command"], list):
            raise ValueError("ProcEntrypoint 'command' must be a list")
        return cls(command=data["command"])


@dataclass
class Entrypoints:
    """Overlay entrypoints configuration."""
    http: Optional[HTTPEntrypoint] = None
    proc: Optional[ProcEntrypoint] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.http:
            result["http"] = self.http.to_dict()
        if self.proc:
            result["proc"] = self.proc.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Entrypoints:
        http = HTTPEntrypoint.from_dict(data["http"]) if "http" in data else None
        proc = ProcEntrypoint.from_dict(data["proc"]) if "proc" in data else None
        return cls(http=http, proc=proc)


@dataclass
class CapabilityDegradation:
    """Degradation settings for a capability."""
    max_fraction: float = 0.5
    disable_nonessential: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_fraction": self.max_fraction,
            "disable_nonessential": self.disable_nonessential,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CapabilityDegradation:
        return cls(
            max_fraction=data.get("max_fraction", 0.5),
            disable_nonessential=data.get("disable_nonessential", True),
        )


@dataclass
class Capability:
    """
    Capability definition for an overlay.

    Specifies how to invoke a specific capability via a runner.
    """
    name: str
    runner: str  # "http" or "proc"
    path: str  # URL path or CLI subcommand
    method: str = "POST"
    timeout_s: int = 30
    default_profile: str = "BALANCED"
    degradation: CapabilityDegradation = field(default_factory=CapabilityDegradation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runner": self.runner,
            "path": self.path,
            "method": self.method,
            "timeout_s": self.timeout_s,
            "default_profile": self.default_profile,
            "degradation": self.degradation.to_dict(),
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> Capability:
        if "runner" not in data:
            raise ValueError(f"Capability '{name}' missing required field 'runner'")
        if "path" not in data:
            raise ValueError(f"Capability '{name}' missing required field 'path'")

        degradation = CapabilityDegradation.from_dict(data.get("degradation", {}))

        return cls(
            name=name,
            runner=data["runner"],
            path=data["path"],
            method=data.get("method", "POST"),
            timeout_s=data.get("timeout_s", 30),
            default_profile=data.get("default_profile", "BALANCED"),
            degradation=degradation,
        )


@dataclass
class Resources:
    """Resource preferences and requirements."""
    prefers_gpu: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prefers_gpu": self.prefers_gpu,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Resources:
        return cls(
            prefers_gpu=data.get("prefers_gpu", False),
            notes=data.get("notes", ""),
        )


@dataclass
class Policy:
    """Execution policy configuration."""
    deterministic: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {"deterministic": self.deterministic}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Policy:
        return cls(deterministic=data.get("deterministic", True))


@dataclass
class OverlayManifest:
    """
    Complete overlay manifest.

    Defines metadata, entrypoints, capabilities, resources, and policies.
    """
    name: str
    version: str
    description: str
    entrypoints: Entrypoints
    capabilities: Dict[str, Capability]
    resources: Resources = field(default_factory=Resources)
    policy: Policy = field(default_factory=Policy)

    def validate(self) -> None:
        """
        Validate manifest consistency.

        Raises:
            ValueError: If manifest is invalid
        """
        if not self.name:
            raise ValueError("Manifest 'name' is required")
        if not self.version:
            raise ValueError("Manifest 'version' is required")
        if not self.capabilities:
            raise ValueError("Manifest must define at least one capability")

        # Validate that capabilities reference valid runners
        for cap_name, cap in self.capabilities.items():
            if cap.runner == "http" and not self.entrypoints.http:
                raise ValueError(
                    f"Capability '{cap_name}' uses 'http' runner but no HTTP entrypoint defined"
                )
            if cap.runner == "proc" and not self.entrypoints.proc:
                raise ValueError(
                    f"Capability '{cap_name}' uses 'proc' runner but no proc entrypoint defined"
                )
            if cap.runner not in ("http", "proc"):
                raise ValueError(
                    f"Capability '{cap_name}' has invalid runner '{cap.runner}' (must be 'http' or 'proc')"
                )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert manifest to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "entrypoints": self.entrypoints.to_dict(),
            "capabilities": {name: cap.to_dict() for name, cap in self.capabilities.items()},
            "resources": self.resources.to_dict(),
            "policy": self.policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OverlayManifest:
        """
        Parse manifest from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            OverlayManifest instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required = ["name", "version", "description", "entrypoints", "capabilities"]
        for field_name in required:
            if field_name not in data:
                raise ValueError(f"Manifest missing required field '{field_name}'")

        # Parse entrypoints
        entrypoints = Entrypoints.from_dict(data["entrypoints"])

        # Parse capabilities
        capabilities = {}
        for cap_name, cap_data in data["capabilities"].items():
            capabilities[cap_name] = Capability.from_dict(cap_name, cap_data)

        # Parse optional fields
        resources = Resources.from_dict(data.get("resources", {}))
        policy = Policy.from_dict(data.get("policy", {}))

        manifest = cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            entrypoints=entrypoints,
            capabilities=capabilities,
            resources=resources,
            policy=policy,
        )

        manifest.validate()
        return manifest

    def save(self, base_path: str = ".aal/overlays") -> None:
        """
        Save manifest to disk.

        Args:
            base_path: Base directory for overlays (default: .aal/overlays)
        """
        manifest_dir = Path(base_path) / self.name
        manifest_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = manifest_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)

    @classmethod
    def load(cls, name: str, base_path: str = ".aal/overlays") -> OverlayManifest:
        """
        Load manifest from disk.

        Args:
            name: Overlay name
            base_path: Base directory for overlays (default: .aal/overlays)

        Returns:
            OverlayManifest instance

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If manifest is invalid
        """
        manifest_path = Path(base_path) / name / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)
