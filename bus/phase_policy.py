from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from .types import Phase

class PolicyViolation(Exception):
    """Raised when a phase policy is violated"""
    def __init__(self, phase: Phase, reason: str, details: Optional[Dict[str, Any]] = None):
        self.phase = phase
        self.reason = reason
        self.details = details or {}
        super().__init__(f"Phase policy violation [{phase}]: {reason}")

class PhasePolicy:
    def __init__(
        self,
        phase: Phase,
        description: str,
        allowed_capabilities: List[str],
        forbidden_capabilities: List[str],
        forbidden_patterns: List[str],
        max_duration_ms: int,
        require_audit: bool,
        require_approval: bool = False,
        require_provenance: bool = False,
        deterministic: bool = False,
        immutable: bool = False,
        notes: Optional[str] = None,
    ):
        self.phase = phase
        self.description = description
        self.allowed_capabilities = set(allowed_capabilities)
        self.forbidden_capabilities = set(forbidden_capabilities)
        self.forbidden_patterns = forbidden_patterns
        self.max_duration_ms = max_duration_ms
        self.require_audit = require_audit
        self.require_approval = require_approval
        self.require_provenance = require_provenance
        self.deterministic = deterministic
        self.immutable = immutable
        self.notes = notes

    def check_capability(self, capability: str) -> None:
        """Raises PolicyViolation if capability is forbidden"""
        if capability in self.forbidden_capabilities:
            raise PolicyViolation(
                self.phase,
                f"Capability '{capability}' is forbidden in {self.phase} phase",
                {"capability": capability, "forbidden": list(self.forbidden_capabilities)}
            )

        # If there's an allowlist and capability not in it, reject
        if self.allowed_capabilities and capability not in self.allowed_capabilities:
            raise PolicyViolation(
                self.phase,
                f"Capability '{capability}' is not allowed in {self.phase} phase",
                {"capability": capability, "allowed": list(self.allowed_capabilities)}
            )

    def check_duration(self, duration_ms: int) -> None:
        """Raises PolicyViolation if duration exceeds limit"""
        if duration_ms > self.max_duration_ms:
            raise PolicyViolation(
                self.phase,
                f"Duration {duration_ms}ms exceeds max {self.max_duration_ms}ms for {self.phase} phase",
                {"duration_ms": duration_ms, "max_duration_ms": self.max_duration_ms}
            )

    def check_entrypoint(self, entrypoint: str) -> None:
        """Raises PolicyViolation if entrypoint contains forbidden patterns"""
        for pattern in self.forbidden_patterns:
            if pattern in entrypoint:
                raise PolicyViolation(
                    self.phase,
                    f"Entrypoint contains forbidden pattern '{pattern}' in {self.phase} phase",
                    {"entrypoint": entrypoint, "pattern": pattern}
                )


class PolicyRegistry:
    def __init__(self, policy_file: Path):
        self.policy_file = policy_file
        self.policies: Dict[Phase, PhasePolicy] = {}
        self._load()

    def _load(self) -> None:
        if not self.policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {self.policy_file}")

        with self.policy_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for phase_name, config in data.items():
            if phase_name not in ("OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"):
                continue

            policy = PhasePolicy(
                phase=phase_name,  # type: ignore
                description=config.get("description", ""),
                allowed_capabilities=config.get("allowed_capabilities", []),
                forbidden_capabilities=config.get("forbidden_capabilities", []),
                forbidden_patterns=config.get("forbidden_patterns", []),
                max_duration_ms=config.get("max_duration_ms", 5000),
                require_audit=config.get("require_audit", False),
                require_approval=config.get("require_approval", False),
                require_provenance=config.get("require_provenance", False),
                deterministic=config.get("deterministic", False),
                immutable=config.get("immutable", False),
                notes=config.get("notes"),
            )
            self.policies[phase_name] = policy  # type: ignore

    def get(self, phase: Phase) -> PhasePolicy:
        if phase not in self.policies:
            raise ValueError(f"No policy defined for phase: {phase}")
        return self.policies[phase]

    def check_execution(
        self,
        phase: Phase,
        entrypoint: str,
        timeout_ms: int,
        capabilities: Optional[List[str]] = None
    ) -> None:
        """
        Validates that execution is allowed under phase policy.
        Raises PolicyViolation if any constraint is violated.
        """
        policy = self.get(phase)

        # Check entrypoint for forbidden patterns
        policy.check_entrypoint(entrypoint)

        # Check timeout doesn't exceed phase limit
        policy.check_duration(timeout_ms)

        # Check declared capabilities (if overlay declares them)
        if capabilities:
            for cap in capabilities:
                policy.check_capability(cap)
