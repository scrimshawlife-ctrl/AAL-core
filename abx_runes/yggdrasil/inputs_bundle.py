from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class InputBundle:
    """
    Declares what data/evidence is available for a given planning run.

    Dtype matching is strict string equality to stay deterministic.
    No inference, no coercion - exact port_name + dtype match required.

    Example:
        bundle = InputBundle(present={
            "news_feed": "jsonl",
            "calendar_events": "ics",
        })

        # Check if port is available:
        bundle.has("news_feed", "jsonl")  # True
        bundle.has("news_feed", "json")   # False (dtype mismatch)
    """
    present: Dict[str, str] = field(default_factory=dict)  # port_name -> dtype

    def has(self, name: str, dtype: str) -> bool:
        """Check if port with exact name + dtype is present."""
        return self.present.get(name) == dtype

    def missing_required(self, required_ports: Tuple) -> Tuple[str, ...]:
        """
        Determine which required ports are missing from this bundle.

        Args:
            required_ports: Tuple of PortSpec objects (or tuples with name, dtype, required)

        Returns:
            Tuple of missing port names (deterministically sorted)
        """
        missing = []
        for p in required_ports:
            # Support both PortSpec objects and tuples
            pname = getattr(p, "name", None) or p[0]
            pdtype = getattr(p, "dtype", None) or p[1]
            preq = getattr(p, "required", None)
            if preq is None:
                preq = (len(p) > 2 and bool(p[2]))

            # Only check required=True ports
            if preq and not self.has(str(pname), str(pdtype)):
                missing.append(str(pname))

        return tuple(sorted(set(missing)))
