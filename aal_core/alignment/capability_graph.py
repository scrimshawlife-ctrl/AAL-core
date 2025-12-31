"""
Capability Graph - Track and constrain agent capabilities

Treats capabilities as a graph where:
- Nodes = skills/tools/data domains
- Edges = compositions (capability chains)
- Weights = bandwidth/rate limits

Prevents accidental capability accretion and dangerous compositions.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass
class CapabilityNode:
    """A single capability (skill, tool, or data domain)"""

    name: str
    description: str
    risk_level: int  # 0-10, where 10 is most dangerous
    requires_approval: bool = False
    max_rate_per_hour: Optional[int] = None

    # Metadata
    added_at: datetime = field(default_factory=datetime.utcnow)
    added_by: Optional[str] = None


@dataclass
class CapabilityEdge:
    """A composition of capabilities"""

    from_cap: str
    to_cap: str
    description: str
    combined_risk: int  # Risk when these are composed
    requires_approval: bool = True

    added_at: datetime = field(default_factory=datetime.utcnow)


class CapabilityGraph:
    """
    Manages the capability graph for an agent.

    Controls what the agent can do and how capabilities can be composed.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.nodes: Dict[str, CapabilityNode] = {}
        self.edges: List[CapabilityEdge] = []

        # Track usage for rate limiting
        self.usage_log: List[Dict] = []

    def add_capability(
        self,
        capability: CapabilityNode,
        human_approver: Optional[str] = None
    ) -> bool:
        """
        Add a new capability to the graph.

        High-risk capabilities require human approval.

        Args:
            capability: Capability to add
            human_approver: ID of human approving this addition

        Returns:
            True if capability was added
        """
        if capability.name in self.nodes:
            log.warning(f"Capability {capability.name} already exists for {self.agent_id}")
            return False

        # Require approval for high-risk capabilities
        if capability.risk_level >= 7 and not human_approver:
            log.error(f"High-risk capability {capability.name} requires human approval")
            return False

        self.nodes[capability.name] = capability
        log.info(
            f"Added capability '{capability.name}' to {self.agent_id} "
            f"(risk={capability.risk_level}, approver={human_approver})"
        )

        return True

    def add_composition(
        self,
        edge: CapabilityEdge,
        human_approver: Optional[str] = None
    ) -> bool:
        """
        Add an edge allowing two capabilities to be composed.

        This is critical: prevents agents from chaining capabilities
        in dangerous ways without oversight.

        Args:
            edge: Composition to allow
            human_approver: ID of human approving this composition

        Returns:
            True if composition was added
        """
        # Validate both capabilities exist
        if edge.from_cap not in self.nodes or edge.to_cap not in self.nodes:
            log.error(f"Cannot add edge: one or both capabilities don't exist")
            return False

        # Most compositions require approval
        if edge.requires_approval and not human_approver:
            log.error(
                f"Composition {edge.from_cap} -> {edge.to_cap} requires human approval"
            )
            return False

        self.edges.append(edge)
        log.info(
            f"Added composition {edge.from_cap} -> {edge.to_cap} for {self.agent_id} "
            f"(combined_risk={edge.combined_risk}, approver={human_approver})"
        )

        return True

    def can_use_capability(self, capability_name: str) -> bool:
        """Check if agent has access to a capability"""
        if capability_name not in self.nodes:
            log.warning(f"Agent {self.agent_id} attempted to use unknown capability: {capability_name}")
            return False

        cap = self.nodes[capability_name]

        # Check rate limiting
        if cap.max_rate_per_hour:
            recent_uses = self._count_recent_uses(capability_name, hours=1)
            if recent_uses >= cap.max_rate_per_hour:
                log.warning(
                    f"Agent {self.agent_id} hit rate limit for {capability_name}: "
                    f"{recent_uses}/{cap.max_rate_per_hour}"
                )
                return False

        return True

    def can_compose_capabilities(self, capability_chain: List[str]) -> bool:
        """
        Check if agent can chain capabilities together.

        Args:
            capability_chain: List of capabilities in order of composition

        Returns:
            True if this composition is allowed
        """
        # All individual capabilities must exist
        for cap in capability_chain:
            if not self.can_use_capability(cap):
                return False

        # Check if edges exist for each step
        for i in range(len(capability_chain) - 1):
            from_cap = capability_chain[i]
            to_cap = capability_chain[i + 1]

            edge_exists = any(
                e.from_cap == from_cap and e.to_cap == to_cap
                for e in self.edges
            )

            if not edge_exists:
                log.warning(
                    f"Agent {self.agent_id} attempted unauthorized composition: "
                    f"{from_cap} -> {to_cap}"
                )
                return False

        return True

    def log_capability_use(self, capability_name: str, metadata: Optional[Dict] = None):
        """Log usage of a capability for auditing and rate limiting"""
        self.usage_log.append({
            "timestamp": datetime.utcnow(),
            "capability": capability_name,
            "metadata": metadata or {},
        })

    def get_risk_profile(self) -> Dict:
        """
        Generate a risk profile for this agent's current capabilities.

        Returns:
            Dictionary with risk metrics
        """
        if not self.nodes:
            return {"max_risk": 0, "avg_risk": 0, "high_risk_count": 0}

        risks = [n.risk_level for n in self.nodes.values()]
        high_risk_capabilities = [
            n.name for n in self.nodes.values() if n.risk_level >= 7
        ]

        # Calculate combined risk from edges
        composition_risks = [e.combined_risk for e in self.edges]

        return {
            "max_risk": max(risks),
            "avg_risk": sum(risks) / len(risks),
            "high_risk_count": len(high_risk_capabilities),
            "high_risk_capabilities": high_risk_capabilities,
            "composition_count": len(self.edges),
            "max_composition_risk": max(composition_risks) if composition_risks else 0,
        }

    def _count_recent_uses(self, capability_name: str, hours: int) -> int:
        """Count how many times a capability was used in recent hours"""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        return sum(
            1 for entry in self.usage_log
            if entry["capability"] == capability_name
            and entry["timestamp"].timestamp() > cutoff
        )


class CapabilityRegistry:
    """
    Global registry of capability graphs for all agents.

    Enforces system-wide capability policies.
    """

    def __init__(self):
        self.graphs: Dict[str, CapabilityGraph] = {}

        # System-wide forbidden compositions (never allowed)
        self.forbidden_compositions: Set[tuple] = {
            ("code_execution", "network_unrestricted"),
            ("self_modify", "autonomous_deploy"),
            ("financial_access", "autonomous_trading"),
        }

    def get_or_create_graph(self, agent_id: str) -> CapabilityGraph:
        """Get existing graph or create new one for agent"""
        if agent_id not in self.graphs:
            self.graphs[agent_id] = CapabilityGraph(agent_id)
        return self.graphs[agent_id]

    def validate_composition(self, from_cap: str, to_cap: str) -> bool:
        """Check if a composition is forbidden system-wide"""
        return (from_cap, to_cap) not in self.forbidden_compositions

    def get_system_risk_summary(self) -> Dict:
        """Get risk summary across all agents"""
        if not self.graphs:
            return {"agent_count": 0, "total_capabilities": 0}

        all_risks = []
        for graph in self.graphs.values():
            profile = graph.get_risk_profile()
            all_risks.append(profile)

        return {
            "agent_count": len(self.graphs),
            "total_capabilities": sum(len(g.nodes) for g in self.graphs.values()),
            "max_risk_across_system": max(r["max_risk"] for r in all_risks),
            "high_risk_agent_count": sum(1 for r in all_risks if r["max_risk"] >= 7),
        }
