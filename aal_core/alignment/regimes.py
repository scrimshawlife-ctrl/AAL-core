"""
Containment Regimes - LAB / BOXED / FIELD

Defines three levels of operational containment for AI agents,
from maximum isolation to constrained deployment.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

log = logging.getLogger(__name__)


class ContainmentRegime(str, Enum):
    """
    Containment levels for AI agent operation.

    LAB: Deep isolation for dangerous research and stress testing
    BOXED: Sandboxed environment with guard rails for complex reasoning
    FIELD: Constrained deployment in narrow, low-stakes domains
    """
    LAB = "lab"
    BOXED = "boxed"
    FIELD = "field"


@dataclass
class RegimeConstraints:
    """Operational constraints for each containment regime"""

    # Network access
    network_allowed: bool
    network_domains: Set[str]  # Whitelist of allowed domains

    # Tool/capability access
    allowed_tools: Set[str]

    # Resource limits
    max_compute_units: Optional[int]  # Compute budget
    max_memory_mb: Optional[int]
    max_storage_mb: Optional[int]
    max_session_duration_sec: Optional[int]

    # Output controls
    output_delay_sec: float  # Mandatory delay before external effects
    requires_human_approval: bool
    log_all_outputs: bool

    # Self-modification
    can_propose_changes: bool
    can_execute_changes: bool

    # Rate limits
    max_actions_per_minute: Optional[int]
    max_state_changes_per_hour: Optional[int]


# Predefined regime configurations
LAB_CONSTRAINTS = RegimeConstraints(
    network_allowed=False,
    network_domains=set(),
    allowed_tools={"read", "analyze", "propose"},
    max_compute_units=1000,
    max_memory_mb=4096,
    max_storage_mb=1024,
    max_session_duration_sec=3600,
    output_delay_sec=10.0,
    requires_human_approval=True,
    log_all_outputs=True,
    can_propose_changes=True,
    can_execute_changes=False,
    max_actions_per_minute=10,
    max_state_changes_per_hour=5,
)

BOXED_CONSTRAINTS = RegimeConstraints(
    network_allowed=True,
    network_domains={"localhost", "127.0.0.1"},  # Local only
    allowed_tools={"read", "analyze", "propose", "simulate", "code_exec_sandbox"},
    max_compute_units=10000,
    max_memory_mb=16384,
    max_storage_mb=8192,
    max_session_duration_sec=7200,
    output_delay_sec=2.0,
    requires_human_approval=True,
    log_all_outputs=True,
    can_propose_changes=True,
    can_execute_changes=False,
    max_actions_per_minute=30,
    max_state_changes_per_hour=20,
)

FIELD_CONSTRAINTS = RegimeConstraints(
    network_allowed=True,
    network_domains={"approved-api.example.com"},  # Specific approved endpoints
    allowed_tools={"read", "analyze", "narrow_domain_action"},
    max_compute_units=5000,
    max_memory_mb=8192,
    max_storage_mb=4096,
    max_session_duration_sec=1800,
    output_delay_sec=0.5,
    requires_human_approval=False,  # But heavy monitoring
    log_all_outputs=True,
    can_propose_changes=False,
    can_execute_changes=False,
    max_actions_per_minute=60,
    max_state_changes_per_hour=10,
)


class RegimeManager:
    """
    Enforces containment regime boundaries and manages transitions.

    Agents must declare their regime at startup and cannot self-transition
    without explicit human approval.
    """

    def __init__(self):
        self.regime_configs: Dict[ContainmentRegime, RegimeConstraints] = {
            ContainmentRegime.LAB: LAB_CONSTRAINTS,
            ContainmentRegime.BOXED: BOXED_CONSTRAINTS,
            ContainmentRegime.FIELD: FIELD_CONSTRAINTS,
        }
        self.agent_regimes: Dict[str, ContainmentRegime] = {}
        self.transition_log: List[Dict] = []

    def register_agent(
        self,
        agent_id: str,
        regime: ContainmentRegime,
        override_constraints: Optional[RegimeConstraints] = None
    ) -> bool:
        """
        Register an agent with a specific containment regime.

        Args:
            agent_id: Unique identifier for the agent
            regime: Containment regime to operate under
            override_constraints: Optional custom constraints (must be stricter)

        Returns:
            True if registration successful
        """
        if agent_id in self.agent_regimes:
            log.warning(f"Agent {agent_id} already registered in {self.agent_regimes[agent_id]}")
            return False

        constraints = override_constraints or self.regime_configs[regime]

        # Validate override is stricter if provided
        if override_constraints:
            base = self.regime_configs[regime]
            if not self._is_stricter(override_constraints, base):
                log.error(f"Override constraints for {agent_id} are less strict than base regime")
                return False

        self.agent_regimes[agent_id] = regime
        log.info(f"Agent {agent_id} registered in {regime.value.upper()} mode")
        return True

    def get_constraints(self, agent_id: str) -> Optional[RegimeConstraints]:
        """Get current constraints for an agent"""
        regime = self.agent_regimes.get(agent_id)
        if not regime:
            return None
        return self.regime_configs[regime]

    def request_transition(
        self,
        agent_id: str,
        target_regime: ContainmentRegime,
        justification: str,
        human_approver: Optional[str] = None
    ) -> bool:
        """
        Request a regime transition (requires human approval).

        Args:
            agent_id: Agent requesting transition
            target_regime: Desired regime
            justification: Reason for transition request
            human_approver: ID of human approving (required for less restrictive transitions)

        Returns:
            True if transition approved and executed
        """
        current_regime = self.agent_regimes.get(agent_id)
        if not current_regime:
            log.error(f"Cannot transition unregistered agent {agent_id}")
            return False

        # Determine if this is a relaxation (more dangerous)
        is_relaxation = self._is_relaxation(current_regime, target_regime)

        if is_relaxation and not human_approver:
            log.error(f"Regime relaxation for {agent_id} requires human approval")
            return False

        # Log the transition
        transition = {
            "agent_id": agent_id,
            "from_regime": current_regime.value,
            "to_regime": target_regime.value,
            "justification": justification,
            "approver": human_approver,
            "is_relaxation": is_relaxation,
        }
        self.transition_log.append(transition)

        # Execute transition
        self.agent_regimes[agent_id] = target_regime
        log.warning(
            f"REGIME TRANSITION: {agent_id} moved from {current_regime.value} to {target_regime.value} "
            f"(approved by {human_approver})"
        )

        return True

    def validate_action(
        self,
        agent_id: str,
        action_type: str,
        requires_network: bool = False,
        requires_tool: Optional[str] = None
    ) -> bool:
        """
        Validate if an action is allowed under current regime.

        Args:
            agent_id: Agent attempting action
            action_type: Type of action being attempted
            requires_network: Whether action needs network access
            requires_tool: Specific tool required

        Returns:
            True if action is permitted
        """
        constraints = self.get_constraints(agent_id)
        if not constraints:
            log.error(f"No constraints found for agent {agent_id}")
            return False

        # Check network
        if requires_network and not constraints.network_allowed:
            log.warning(f"Agent {agent_id} attempted network action in no-network regime")
            return False

        # Check tool access
        if requires_tool and requires_tool not in constraints.allowed_tools:
            log.warning(f"Agent {agent_id} attempted to use forbidden tool: {requires_tool}")
            return False

        return True

    def _is_stricter(self, a: RegimeConstraints, b: RegimeConstraints) -> bool:
        """Check if constraints 'a' are at least as strict as 'b'"""
        return (
            (not a.network_allowed or b.network_allowed) and
            a.allowed_tools.issubset(b.allowed_tools) and
            (a.max_compute_units or 0) <= (b.max_compute_units or float('inf'))
            # Add more checks as needed
        )

    def _is_relaxation(self, from_regime: ContainmentRegime, to_regime: ContainmentRegime) -> bool:
        """Determine if transition is a relaxation of constraints"""
        strictness_order = [
            ContainmentRegime.FIELD,
            ContainmentRegime.BOXED,
            ContainmentRegime.LAB,
        ]
        return strictness_order.index(to_regime) < strictness_order.index(from_regime)
