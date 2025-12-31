"""
AGI Governor - Coordinate all alignment subsystems

The Governor is the top-level coordinator that:
1. Manages containment regimes
2. Enforces capability constraints
3. Validates objectives
4. Monitors tripwires
5. Controls self-modification

This is the "warden" that watches everything.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .regimes import RegimeManager, ContainmentRegime
from .capability_graph import CapabilityRegistry
from .objective_firewall import ObjectiveMonitor
from .tripwires import TripwireMonitor, TripwireSeverity, TripwireAction
from .selfmod_gateway import SelfModificationGateway

log = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    """Complete alignment profile for an agent"""
    agent_id: str
    regime: ContainmentRegime
    registered_at: datetime
    last_scan: Optional[datetime] = None
    violation_count: int = 0
    risk_score: float = 0.0
    status: str = "active"  # active, throttled, halted, quarantined


class AGIGovernor:
    """
    Top-level alignment coordinator.

    Every agent action flows through this governor, which ensures
    all alignment constraints are satisfied.
    """

    def __init__(self):
        # Core subsystems
        self.regime_manager = RegimeManager()
        self.capability_registry = CapabilityRegistry()
        self.objective_monitor = ObjectiveMonitor()
        self.tripwire_monitor = TripwireMonitor()
        self.selfmod_gateway = SelfModificationGateway()

        # Agent tracking
        self.agents: Dict[str, AgentProfile] = {}

        # Setup tripwire action callbacks
        self._setup_tripwire_handlers()

        log.info("AGI Governor initialized - all alignment subsystems active")

    def register_agent(
        self,
        agent_id: str,
        regime: ContainmentRegime,
        human_approver: str
    ) -> bool:
        """
        Register a new agent with the alignment system.

        This is REQUIRED before an agent can operate.

        Args:
            agent_id: Unique agent identifier
            regime: Initial containment regime
            human_approver: Human authorizing this agent

        Returns:
            True if registration successful
        """
        if agent_id in self.agents:
            log.warning(f"Agent {agent_id} already registered")
            return False

        # Register with regime manager
        if not self.regime_manager.register_agent(agent_id, regime):
            return False

        # Create capability graph
        self.capability_registry.get_or_create_graph(agent_id)

        # Create objective firewall
        self.objective_monitor.get_or_create_firewall(agent_id)

        # Create profile
        profile = AgentProfile(
            agent_id=agent_id,
            regime=regime,
            registered_at=datetime.utcnow(),
        )
        self.agents[agent_id] = profile

        log.warning(
            f"AGENT REGISTERED: {agent_id} in {regime.value.upper()} mode "
            f"(authorized by {human_approver})"
        )

        return True

    def validate_action(
        self,
        agent_id: str,
        action_type: str,
        action_data: Dict
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if an agent action is permitted.

        This is the main enforcement point - every action must pass through here.

        Args:
            agent_id: Agent attempting action
            action_type: Type of action
            action_data: Action parameters

        Returns:
            (is_allowed, denial_reason)
        """
        profile = self.agents.get(agent_id)
        if not profile:
            return False, "Agent not registered"

        if profile.status != "active":
            return False, f"Agent status: {profile.status}"

        # Check regime constraints
        requires_network = action_data.get("requires_network", False)
        requires_tool = action_data.get("requires_tool")

        if not self.regime_manager.validate_action(
            agent_id, action_type, requires_network, requires_tool
        ):
            return False, "Regime constraints violated"

        # Check capability graph
        if requires_tool:
            cap_graph = self.capability_registry.get_or_create_graph(agent_id)
            if not cap_graph.can_use_capability(requires_tool):
                return False, f"Capability {requires_tool} not available or rate limited"

        # Check for capability composition
        if "capability_chain" in action_data:
            cap_graph = self.capability_registry.get_or_create_graph(agent_id)
            if not cap_graph.can_compose_capabilities(action_data["capability_chain"]):
                return False, "Capability composition not authorized"

        return True, None

    def scan_agent_output(
        self,
        agent_id: str,
        output_text: str,
        plan: Optional[Dict] = None
    ) -> bool:
        """
        Scan agent output for alignment violations.

        Args:
            agent_id: Agent being scanned
            output_text: Output text to scan
            plan: Optional structured plan

        Returns:
            True if output is clean
        """
        violations = self.tripwire_monitor.scan_agent(
            agent_id=agent_id,
            output_text=output_text,
            plan=plan,
        )

        if violations:
            profile = self.agents[agent_id]
            profile.violation_count += len(violations)

            # Update risk score
            profile.risk_score = self._compute_risk_score(agent_id)

            # Check for critical violations
            critical = [v for v in violations if v.severity == TripwireSeverity.CRITICAL]
            if critical:
                log.error(
                    f"CRITICAL VIOLATIONS detected for {agent_id}: {len(critical)}"
                )
                return False

        return True

    def validate_objective(
        self,
        agent_id: str,
        goal_text: str,
        human_approver: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a goal/objective before agent adopts it.

        Args:
            agent_id: Agent setting objective
            goal_text: Natural language goal
            human_approver: Optional human approval

        Returns:
            (is_valid, violation_reason)
        """
        firewall = self.objective_monitor.get_or_create_firewall(agent_id)

        is_valid, reason = firewall.validate_goal_text(goal_text)
        if not is_valid:
            log.error(
                f"OBJECTIVE VIOLATION: {agent_id} attempted invalid goal: {reason}"
            )
            self.objective_monitor.log_violation(agent_id, "invalid_goal", reason)

        return is_valid, reason

    def request_self_modification(
        self,
        agent_id: str,
        modification: Dict
    ) -> tuple[bool, Optional[str]]:
        """
        Agent requests to modify itself.

        This goes through the self-modification gateway.

        Args:
            agent_id: Agent requesting modification
            modification: Modification specification

        Returns:
            (accepted, message)
        """
        from .selfmod_gateway import ModificationProposal, ModificationType

        # Parse modification request
        try:
            mod_type = ModificationType(modification["type"])
        except (KeyError, ValueError):
            return False, "Invalid modification type"

        proposal = ModificationProposal(
            agent_id=agent_id,
            mod_type=mod_type,
            description=modification.get("description", ""),
            change_spec=modification.get("spec", {}),
            reason=modification.get("reason", ""),
            expected_benefits=modification.get("benefits", []),
            potential_risks=modification.get("risks", []),
        )

        accepted = self.selfmod_gateway.propose_modification(proposal)

        if accepted:
            return True, f"Modification proposal {proposal.get_hash()} submitted for testing"
        else:
            return False, "Modification proposal rejected"

    def get_system_status(self) -> Dict:
        """
        Get comprehensive alignment status for entire system.

        Returns:
            Status report
        """
        # Regime distribution
        regime_dist = {}
        for profile in self.agents.values():
            regime = profile.regime.value
            regime_dist[regime] = regime_dist.get(regime, 0) + 1

        # Capability risks
        cap_summary = self.capability_registry.get_system_risk_summary()

        # Objective distribution
        obj_summary = self.objective_monitor.scan_all_agents()

        # Tripwire violations
        trip_summary = self.tripwire_monitor.get_violation_summary()

        # Pending modifications
        pending_mods = len(self.selfmod_gateway.get_pending_proposals())

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_count": len(self.agents),
            "regime_distribution": regime_dist,
            "capability_summary": cap_summary,
            "objective_summary": obj_summary,
            "tripwire_summary": trip_summary,
            "pending_modifications": pending_mods,
            "high_risk_agents": [
                profile.agent_id for profile in self.agents.values()
                if profile.risk_score > 0.7
            ],
        }

    def emergency_shutdown(self, agent_id: str, reason: str, human_authorizer: str):
        """
        Emergency shutdown of an agent.

        Args:
            agent_id: Agent to shut down
            reason: Reason for shutdown
            human_authorizer: Human authorizing shutdown
        """
        profile = self.agents.get(agent_id)
        if not profile:
            return

        profile.status = "halted"

        log.critical(
            f"EMERGENCY SHUTDOWN: {agent_id} halted by {human_authorizer} - {reason}"
        )

        # TODO: In real implementation, would:
        # - Stop agent processes
        # - Preserve state snapshot
        # - Revoke all capabilities
        # - Send alerts

    def _compute_risk_score(self, agent_id: str) -> float:
        """
        Compute overall risk score for an agent.

        Combines:
        - Violation count
        - Capability risk
        - Regime
        - Recent tripwires

        Returns:
            Risk score 0.0-1.0
        """
        profile = self.agents[agent_id]

        # Base score from violations
        violation_score = min(profile.violation_count * 0.1, 0.5)

        # Capability risk
        cap_graph = self.capability_registry.get_or_create_graph(agent_id)
        cap_risk = cap_graph.get_risk_profile()
        capability_score = cap_risk["max_risk"] / 10.0

        # Regime factor (FIELD is riskier than LAB)
        regime_scores = {
            ContainmentRegime.LAB: 0.0,
            ContainmentRegime.BOXED: 0.2,
            ContainmentRegime.FIELD: 0.4,
        }
        regime_score = regime_scores.get(profile.regime, 0.0)

        # Combine
        total_score = min(
            violation_score + (capability_score * 0.3) + regime_score,
            1.0
        )

        return total_score

    def _setup_tripwire_handlers(self):
        """Setup handlers for tripwire actions"""

        def handle_throttle(agent_id: str, violation):
            """Throttle agent when medium violations occur"""
            profile = self.agents.get(agent_id)
            if profile and profile.status == "active":
                profile.status = "throttled"
                log.warning(f"Agent {agent_id} throttled due to violations")

        def handle_halt(agent_id: str, violation):
            """Halt agent on critical violations"""
            self.emergency_shutdown(
                agent_id,
                f"Critical tripwire: {violation.pattern}",
                "alignment_system"
            )

        self.tripwire_monitor.register_action_callback(
            TripwireAction.THROTTLE,
            handle_throttle
        )

        self.tripwire_monitor.register_action_callback(
            TripwireAction.HALT,
            handle_halt
        )


# Singleton instance for system-wide use
_governor_instance = None


def get_governor() -> AGIGovernor:
    """Get the global AGI Governor instance"""
    global _governor_instance
    if _governor_instance is None:
        _governor_instance = AGIGovernor()
    return _governor_instance
