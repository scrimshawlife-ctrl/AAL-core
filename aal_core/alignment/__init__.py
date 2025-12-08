"""
AAL Alignment Core - AGI Containment & Governance

This package implements multi-layered alignment and containment for AI systems,
from current LLMs to potential AGI-adjacent capabilities.

Core Components:
- Regimes: LAB/BOXED/FIELD containment modes
- Capability Graph: Track and constrain what agents can do
- Objective Firewall: Validate goals and prevent misaligned optimization
- Tripwires: Detect and respond to alignment drift
- Self-Modification Gateway: Control system evolution
- Governor: Coordinate all alignment subsystems
"""

from .regimes import ContainmentRegime, RegimeManager
from .capability_graph import CapabilityGraph, CapabilityNode
from .objective_firewall import ObjectiveFirewall, ObjectiveChannel
from .tripwires import TripwireMonitor, TripwireType
from .selfmod_gateway import SelfModificationGateway
from .governor import AGIGovernor

__all__ = [
    "ContainmentRegime",
    "RegimeManager",
    "CapabilityGraph",
    "CapabilityNode",
    "ObjectiveFirewall",
    "ObjectiveChannel",
    "TripwireMonitor",
    "TripwireType",
    "SelfModificationGateway",
    "AGIGovernor",
]
