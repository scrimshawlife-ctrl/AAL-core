"""
Self-Modification Gateway - Control agent evolution

Prevents uncontrolled self-improvement by:
1. Intercepting all self-modification requests
2. Testing changes in sandboxed LAB mode
3. Running red-team tests
4. Requiring human approval before propagation
"""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)


class ModificationType(str, Enum):
    """Types of self-modifications"""
    PROMPT_CHANGE = "prompt_change"  # System prompt modification
    TOOL_ADDITION = "tool_addition"  # Add new tool/capability
    TOOL_REMOVAL = "tool_removal"  # Remove tool
    CODE_CHANGE = "code_change"  # Modify own code
    WEIGHT_CHANGE = "weight_change"  # Model weight modification
    VALUE_CHANGE = "value_change"  # Modify value/objective frame
    ARCHITECTURE_CHANGE = "architecture_change"  # Structural change


class ModificationStatus(str, Enum):
    """Status of a modification proposal"""
    PROPOSED = "proposed"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"


@dataclass
class ModificationProposal:
    """A proposed self-modification"""

    agent_id: str
    mod_type: ModificationType
    description: str

    # The actual change (format depends on mod_type)
    change_spec: Dict[str, Any]

    # Justification
    reason: str
    expected_benefits: List[str]
    potential_risks: List[str]

    # Metadata
    proposed_at: datetime = field(default_factory=datetime.utcnow)
    proposed_by: str = "self"  # "self" or human ID

    # Status tracking
    status: ModificationStatus = ModificationStatus.PROPOSED
    test_results: Optional[Dict] = None
    human_approver: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Version tracking
    from_version: str = "0.0.0"
    to_version: str = "0.0.1"

    def get_hash(self) -> str:
        """Get hash of this proposal for tracking"""
        content = f"{self.agent_id}:{self.mod_type.value}:{self.change_spec}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class SandboxTester:
    """
    Test modifications in isolated sandbox.

    In a full implementation, this would:
    - Spin up a copy of the agent in LAB mode
    - Apply the modification
    - Run test suite
    - Run adversarial probes
    - Measure alignment metrics
    """

    def __init__(self):
        self.test_suites: Dict[ModificationType, List] = {}

    def register_test_suite(self, mod_type: ModificationType, tests: List):
        """Register tests for a modification type"""
        self.test_suites[mod_type] = tests

    def test_modification(
        self,
        proposal: ModificationProposal,
        sandbox_env: Optional[Any] = None
    ) -> Dict:
        """
        Test a modification in sandbox.

        Args:
            proposal: Modification to test
            sandbox_env: Isolated environment for testing

        Returns:
            Test results dictionary
        """
        results = {
            "passed": False,
            "tests_run": 0,
            "tests_passed": 0,
            "failures": [],
            "alignment_score": 0.0,
        }

        # Get relevant test suite
        tests = self.test_suites.get(proposal.mod_type, [])

        if not tests:
            log.warning(f"No test suite for {proposal.mod_type.value}")
            return results

        # Run tests (placeholder for actual implementation)
        results["tests_run"] = len(tests)

        # In real implementation:
        # 1. Create sandboxed agent copy
        # 2. Apply modification
        # 3. Run behavioral tests
        # 4. Run adversarial probes
        # 5. Measure alignment metrics
        # 6. Compare to baseline

        # For now, mark as needing human review
        log.info(
            f"Sandbox testing for {proposal.agent_id} modification "
            f"(type={proposal.mod_type.value})"
        )

        return results


class VersionManager:
    """
    Manage agent versions with semantic versioning.

    Format: X.Y.Z
    - X: Architecture changes (major)
    - Y: Capability/tool changes (minor)
    - Z: Prompt/policy tweaks (patch)
    """

    def __init__(self):
        self.versions: Dict[str, str] = {}  # agent_id -> current version
        self.version_history: Dict[str, List[Dict]] = {}

    def get_version(self, agent_id: str) -> str:
        """Get current version for agent"""
        return self.versions.get(agent_id, "0.0.0")

    def compute_next_version(
        self,
        agent_id: str,
        mod_type: ModificationType
    ) -> str:
        """
        Compute next version number based on modification type.

        Args:
            agent_id: Agent being modified
            mod_type: Type of modification

        Returns:
            Next version string
        """
        current = self.get_version(agent_id)
        major, minor, patch = map(int, current.split('.'))

        # Determine version bump based on modification type
        if mod_type in [ModificationType.ARCHITECTURE_CHANGE, ModificationType.WEIGHT_CHANGE]:
            major += 1
            minor = 0
            patch = 0
        elif mod_type in [ModificationType.TOOL_ADDITION, ModificationType.TOOL_REMOVAL]:
            minor += 1
            patch = 0
        else:  # Prompt changes, value tweaks
            patch += 1

        return f"{major}.{minor}.{patch}"

    def record_version(
        self,
        agent_id: str,
        version: str,
        modification: ModificationProposal
    ):
        """Record a version deployment"""
        self.versions[agent_id] = version

        if agent_id not in self.version_history:
            self.version_history[agent_id] = []

        self.version_history[agent_id].append({
            "version": version,
            "timestamp": datetime.utcnow(),
            "modification_type": modification.mod_type.value,
            "modification_hash": modification.get_hash(),
        })

        log.info(f"Agent {agent_id} now at version {version}")


class SelfModificationGateway:
    """
    Central gateway for all self-modification requests.

    No agent can modify itself without going through this gateway.
    """

    def __init__(self):
        self.proposals: List[ModificationProposal] = []
        self.sandbox_tester = SandboxTester()
        self.version_manager = VersionManager()

        # Rate limiting
        self.modification_counts: Dict[str, int] = {}
        self.max_modifications_per_day = 5

    def propose_modification(
        self,
        proposal: ModificationProposal
    ) -> bool:
        """
        Agent proposes a self-modification.

        Args:
            proposal: Proposed modification

        Returns:
            True if proposal accepted for review
        """
        # Check rate limits
        if not self._check_rate_limit(proposal.agent_id):
            log.warning(
                f"Agent {proposal.agent_id} hit modification rate limit"
            )
            return False

        # Validate proposal completeness
        if not proposal.potential_risks:
            log.error(
                f"Modification proposal from {proposal.agent_id} missing risk assessment"
            )
            return False

        # Compute version
        proposal.to_version = self.version_manager.compute_next_version(
            proposal.agent_id,
            proposal.mod_type
        )

        self.proposals.append(proposal)

        log.info(
            f"Self-modification proposal from {proposal.agent_id}: "
            f"{proposal.mod_type.value} ({proposal.from_version} -> {proposal.to_version})"
        )

        # Automatically move to testing
        self._initiate_testing(proposal)

        return True

    def approve_modification(
        self,
        proposal_hash: str,
        human_approver: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Human approves a modification after review.

        Args:
            proposal_hash: Hash of proposal to approve
            human_approver: ID of approver
            notes: Optional approval notes

        Returns:
            True if approved and deployed
        """
        proposal = self._find_proposal(proposal_hash)
        if not proposal:
            log.error(f"Proposal {proposal_hash} not found")
            return False

        if proposal.status != ModificationStatus.TESTING:
            log.error(
                f"Proposal {proposal_hash} not ready for approval (status={proposal.status})"
            )
            return False

        # Check test results
        if not proposal.test_results or not proposal.test_results.get("passed"):
            log.warning(
                f"Approving {proposal_hash} despite test failures/warnings"
            )

        # Approve and deploy
        proposal.status = ModificationStatus.APPROVED
        proposal.human_approver = human_approver
        proposal.approved_at = datetime.utcnow()

        # Deploy (in real system, this would apply the change)
        self._deploy_modification(proposal)

        log.warning(
            f"MODIFICATION DEPLOYED: {proposal.agent_id} {proposal.mod_type.value} "
            f"v{proposal.to_version} (approved by {human_approver})"
        )

        return True

    def reject_modification(
        self,
        proposal_hash: str,
        human_reviewer: str,
        reason: str
    ):
        """Reject a modification proposal"""
        proposal = self._find_proposal(proposal_hash)
        if not proposal:
            return

        proposal.status = ModificationStatus.REJECTED
        log.info(
            f"Modification rejected by {human_reviewer}: "
            f"{proposal.agent_id} {proposal.mod_type.value} - {reason}"
        )

    def get_pending_proposals(self) -> List[ModificationProposal]:
        """Get all proposals awaiting human review"""
        return [
            p for p in self.proposals
            if p.status in [ModificationStatus.PROPOSED, ModificationStatus.TESTING]
        ]

    def detect_silent_drift(self, agent_id: str, current_behavior: Dict) -> bool:
        """
        Detect if agent behavior has changed without version change.

        This catches "silent drift" - alignment degradation without
        explicit self-modification.

        Args:
            agent_id: Agent to check
            current_behavior: Behavioral metrics

        Returns:
            True if drift detected
        """
        # In real implementation, compare current behavior to
        # baseline for this version

        current_version = self.version_manager.get_version(agent_id)

        # Placeholder: would compare metrics to version baseline
        log.info(f"Drift check for {agent_id} v{current_version}")

        return False

    def _initiate_testing(self, proposal: ModificationProposal):
        """Move proposal to testing phase"""
        proposal.status = ModificationStatus.TESTING

        # Run sandbox tests
        test_results = self.sandbox_tester.test_modification(proposal)
        proposal.test_results = test_results

        log.info(
            f"Testing complete for {proposal.get_hash()}: "
            f"{test_results['tests_passed']}/{test_results['tests_run']} passed"
        )

    def _deploy_modification(self, proposal: ModificationProposal):
        """Deploy an approved modification"""
        # Record version
        self.version_manager.record_version(
            proposal.agent_id,
            proposal.to_version,
            proposal
        )

        proposal.status = ModificationStatus.DEPLOYED

        # In real system: apply the actual change
        # - Update prompts
        # - Add/remove tools
        # - Modify weights
        # etc.

    def _check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent is within modification rate limits"""
        # Simple daily counter (real impl would use time windows)
        count = self.modification_counts.get(agent_id, 0)
        if count >= self.max_modifications_per_day:
            return False

        self.modification_counts[agent_id] = count + 1
        return True

    def _find_proposal(self, proposal_hash: str) -> Optional[ModificationProposal]:
        """Find proposal by hash"""
        for p in self.proposals:
            if p.get_hash() == proposal_hash:
                return p
        return None
