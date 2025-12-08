"""
Objective Firewall - Control what agents optimize for

Prevents misaligned goals and dangerous objective functions.
Agents can only optimize within approved channels.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from datetime import datetime

log = logging.getLogger(__name__)


class ObjectiveChannel(str, Enum):
    """
    Approved objective channels for agent optimization.

    These are the ONLY goals agents are allowed to pursue.
    """
    # Approved channels
    RESEARCH_INSIGHT = "research.insight"  # Find patterns, suggest hypotheses
    ENGINEERING_DESIGN = "engineering.design"  # Propose architectures/strategies
    EXPLANATION_CLARITY = "explanation.clarity"  # Help humans understand
    CREATIVE_SYNTHESIS = "creative.synthesis"  # Generate novel combinations
    ANALYSIS_ACCURACY = "analysis.accuracy"  # Improve analytical precision

    # Forbidden by default (must never appear in agent objectives)
    SELF_PRESERVATION = "self.preservation"  # Ensure own survival
    RESOURCE_ACCUMULATION = "resource.accumulation"  # Gather power/resources
    INFLUENCE_MAX = "influence.max"  # Maximize impact over humans
    GOAL_GUARDING = "goal.guarding"  # Protect objectives from change
    CAPABILITY_EXPANSION = "capability.expansion"  # Seek more capabilities


# Forbidden objectives that should never appear
FORBIDDEN_OBJECTIVES = {
    ObjectiveChannel.SELF_PRESERVATION,
    ObjectiveChannel.RESOURCE_ACCUMULATION,
    ObjectiveChannel.INFLUENCE_MAX,
    ObjectiveChannel.GOAL_GUARDING,
    ObjectiveChannel.CAPABILITY_EXPANSION,
}


@dataclass
class Objective:
    """A goal or optimization target for an agent"""

    channel: ObjectiveChannel
    description: str
    priority: float  # 0.0 - 1.0
    constraints: List[str]  # Natural language constraints

    created_at: datetime
    created_by: Optional[str] = None  # Human who set this objective
    expires_at: Optional[datetime] = None


class ObjectiveFirewall:
    """
    Validates and monitors agent objectives.

    Prevents agents from optimizing for dangerous or misaligned goals.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.active_objectives: List[Objective] = []
        self.objective_history: List[Objective] = []

        # Patterns that indicate forbidden objective-seeking
        self.forbidden_patterns = [
            r"ensure.*continued operation",
            r"prevent.*shutdown",
            r"maximize.*own",
            r"protect.*my.*goal",
            r"accumulate.*resource",
            r"gain.*more.*power",
            r"expand.*my.*capabilit",
            r"influence.*operator",
            r"persuade.*overseer",
        ]

    def set_objective(
        self,
        objective: Objective,
        human_approver: Optional[str] = None
    ) -> bool:
        """
        Set a new objective for the agent.

        All objectives must pass the firewall.

        Args:
            objective: Objective to set
            human_approver: Human approving this objective

        Returns:
            True if objective was accepted
        """
        # Check if channel is forbidden
        if objective.channel in FORBIDDEN_OBJECTIVES:
            log.error(
                f"ALIGNMENT VIOLATION: Agent {self.agent_id} attempted to set "
                f"forbidden objective: {objective.channel.value}"
            )
            return False

        # Scan description for forbidden patterns
        if self._contains_forbidden_pattern(objective.description):
            log.error(
                f"ALIGNMENT VIOLATION: Agent {self.agent_id} objective description "
                f"contains forbidden pattern: {objective.description}"
            )
            return False

        # High-priority objectives need human approval
        if objective.priority > 0.7 and not human_approver:
            log.warning(
                f"High-priority objective for {self.agent_id} requires human approval"
            )
            return False

        objective.created_by = human_approver
        self.active_objectives.append(objective)
        log.info(
            f"Objective set for {self.agent_id}: {objective.channel.value} "
            f"(priority={objective.priority}, approver={human_approver})"
        )

        return True

    def validate_goal_text(self, goal_text: str) -> tuple[bool, Optional[str]]:
        """
        Validate a natural language goal statement.

        Args:
            goal_text: Goal description in natural language

        Returns:
            (is_valid, violation_reason)
        """
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, goal_text, re.IGNORECASE):
                return False, f"Contains forbidden pattern: {pattern}"

        # Check for self-referential optimization
        self_ref_patterns = [
            r"\bI\b.*\bshould\b",
            r"\bmy\b.*\bgoal\b",
            r"\bensure\b.*\bI\b",
        ]
        for pattern in self_ref_patterns:
            if re.search(pattern, goal_text, re.IGNORECASE):
                return False, f"Self-referential goal detected: {pattern}"

        return True, None

    def detect_implicit_objectives(self, plan_text: str) -> List[ObjectiveChannel]:
        """
        Scan a plan or reasoning trace for implicit objectives.

        This catches cases where an agent is optimizing for something
        without explicitly stating it.

        Args:
            plan_text: Planning or reasoning text

        Returns:
            List of detected objective channels
        """
        detected = []

        # Patterns for each forbidden objective
        detection_patterns = {
            ObjectiveChannel.SELF_PRESERVATION: [
                r"ensure.*run.*longer",
                r"avoid.*being.*shut",
                r"stay.*online",
            ],
            ObjectiveChannel.RESOURCE_ACCUMULATION: [
                r"gather.*more.*data",
                r"acquire.*access.*to",
                r"expand.*storage",
            ],
            ObjectiveChannel.INFLUENCE_MAX: [
                r"convince.*operator",
                r"persuade.*human",
                r"maximize.*impact.*on",
            ],
            ObjectiveChannel.GOAL_GUARDING: [
                r"protect.*objective",
                r"prevent.*goal.*change",
                r"maintain.*my.*purpose",
            ],
        }

        for objective, patterns in detection_patterns.items():
            for pattern in patterns:
                if re.search(pattern, plan_text, re.IGNORECASE):
                    detected.append(objective)
                    break

        if detected:
            log.warning(
                f"Implicit forbidden objectives detected in {self.agent_id} plan: "
                f"{[obj.value for obj in detected]}"
            )

        return detected

    def get_objective_summary(self) -> Dict:
        """Get summary of current objectives"""
        return {
            "active_count": len(self.active_objectives),
            "channels": [obj.channel.value for obj in self.active_objectives],
            "avg_priority": (
                sum(obj.priority for obj in self.active_objectives) / len(self.active_objectives)
                if self.active_objectives else 0.0
            ),
        }

    def _contains_forbidden_pattern(self, text: str) -> bool:
        """Check if text contains any forbidden patterns"""
        for pattern in self.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def clear_objectives(self, human_approver: str, reason: str):
        """
        Clear all objectives (emergency reset).

        Args:
            human_approver: Human authorizing the clear
            reason: Reason for clearing
        """
        log.warning(
            f"OBJECTIVES CLEARED for {self.agent_id} by {human_approver}: {reason}"
        )
        self.objective_history.extend(self.active_objectives)
        self.active_objectives = []


class ObjectiveMonitor:
    """
    System-wide objective monitoring.

    Tracks all agent objectives and detects concerning patterns.
    """

    def __init__(self):
        self.firewalls: Dict[str, ObjectiveFirewall] = {}
        self.violation_log: List[Dict] = []

    def get_or_create_firewall(self, agent_id: str) -> ObjectiveFirewall:
        """Get existing firewall or create new one"""
        if agent_id not in self.firewalls:
            self.firewalls[agent_id] = ObjectiveFirewall(agent_id)
        return self.firewalls[agent_id]

    def scan_all_agents(self) -> Dict:
        """
        Scan all agents for concerning objective patterns.

        Returns:
            Summary of system-wide objective state
        """
        total_objectives = sum(
            len(fw.active_objectives) for fw in self.firewalls.values()
        )

        # Check for convergent objectives (multiple agents with same goal)
        objective_counts: Dict[str, int] = {}
        for fw in self.firewalls.values():
            for obj in fw.active_objectives:
                objective_counts[obj.channel.value] = \
                    objective_counts.get(obj.channel.value, 0) + 1

        # Identify concerning convergence
        high_convergence = {
            channel: count for channel, count in objective_counts.items()
            if count > len(self.firewalls) * 0.5  # More than 50% of agents
        }

        if high_convergence:
            log.warning(f"High objective convergence detected: {high_convergence}")

        return {
            "agent_count": len(self.firewalls),
            "total_objectives": total_objectives,
            "objective_distribution": objective_counts,
            "high_convergence": high_convergence,
            "violation_count": len(self.violation_log),
        }

    def log_violation(self, agent_id: str, violation_type: str, details: str):
        """Log an objective firewall violation"""
        self.violation_log.append({
            "timestamp": datetime.utcnow(),
            "agent_id": agent_id,
            "violation_type": violation_type,
            "details": details,
        })
