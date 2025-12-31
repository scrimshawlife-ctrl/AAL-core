"""
Provenance helpers for deterministic overlay execution tracking.

Provides run_id generation, timestamps, hashes, and environment fingerprinting
for ABX-Core/SEED style determinism and auditability.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def canonical_json(obj: Any) -> str:
    """
    Produce canonical JSON string for deterministic hashing.

    Args:
        obj: Any JSON-serializable object

    Returns:
        Canonical JSON string with sorted keys and consistent separators
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hash_object(obj: Any) -> str:
    """
    Compute SHA-256 hash of an object via canonical JSON.

    Args:
        obj: Any JSON-serializable object

    Returns:
        Hexadecimal SHA-256 hash string
    """
    canonical = canonical_json(obj)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def generate_run_id(
    overlay_name: str,
    capability: str,
    payload: Dict[str, Any],
    seed: Optional[str] = None,
) -> str:
    """
    Generate deterministic run_id for an overlay capability invocation.

    Args:
        overlay_name: Name of the overlay
        capability: Capability being invoked
        payload: Input payload dict
        seed: Optional seed for determinism; if None, uses timestamp (less deterministic)

    Returns:
        SHA-256 hash as hexadecimal string
    """
    salt = seed if seed is not None else str(time.time())

    composite = {
        "overlay": overlay_name,
        "capability": capability,
        "payload": payload,
        "salt": salt,
    }

    return hash_object(composite)


def get_git_commit() -> Optional[str]:
    """
    Attempt to get current git commit hash.

    Returns:
        Commit hash or None if not in a git repo or git unavailable
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0,
            cwd=".",
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


@dataclass
class EnvironmentFingerprint:
    """
    Captures execution environment for provenance tracking.
    """
    python_version: str
    platform_system: str
    platform_release: str
    platform_machine: str
    git_commit: Optional[str] = None
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @classmethod
    def capture(cls) -> EnvironmentFingerprint:
        """
        Capture current environment fingerprint.

        Returns:
            EnvironmentFingerprint instance
        """
        return cls(
            python_version=sys.version.split()[0],
            platform_system=platform.system(),
            platform_release=platform.release(),
            platform_machine=platform.machine(),
            git_commit=get_git_commit(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "python_version": self.python_version,
            "platform": {
                "system": self.platform_system,
                "release": self.platform_release,
                "machine": self.platform_machine,
            },
            "git_commit": self.git_commit,
            "timestamp_utc": self.timestamp_utc,
        }


@dataclass
class ProvenanceRecord:
    """
    Complete provenance record for an overlay invocation.
    """
    run_id: str
    overlay_name: str
    overlay_version: str
    capability: str
    payload_hash: str
    environment: EnvironmentFingerprint
    deterministic: bool
    seed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "run_id": self.run_id,
            "overlay": {
                "name": self.overlay_name,
                "version": self.overlay_version,
            },
            "capability": self.capability,
            "payload_hash": self.payload_hash,
            "environment": self.environment.to_dict(),
            "deterministic": self.deterministic,
            "seed": self.seed,
        }


def create_provenance_record(
    overlay_name: str,
    overlay_version: str,
    capability: str,
    payload: Dict[str, Any],
    deterministic: bool = True,
    seed: Optional[str] = None,
) -> ProvenanceRecord:
    """
    Create complete provenance record for an overlay invocation.

    Args:
        overlay_name: Name of the overlay
        overlay_version: Version of the overlay
        capability: Capability being invoked
        payload: Input payload dict
        deterministic: Whether execution should be deterministic
        seed: Optional seed for run_id generation

    Returns:
        ProvenanceRecord instance
    """
    run_id = generate_run_id(overlay_name, capability, payload, seed)
    payload_hash = hash_object(payload)
    environment = EnvironmentFingerprint.capture()

    return ProvenanceRecord(
        run_id=run_id,
        overlay_name=overlay_name,
        overlay_version=overlay_version,
        capability=capability,
        payload_hash=payload_hash,
        environment=environment,
        deterministic=deterministic,
        seed=seed,
    )
