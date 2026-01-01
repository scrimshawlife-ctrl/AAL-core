from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BudgetState:
    """
    Minimal budget tracker for bounded canary/promotion execution.
    """

    canary_remaining: int
    risk_units_remaining: float
    global_active_perturbations: int
    global_active_cap: int

    def charge_canary(self, n: int = 1) -> None:
        self.canary_remaining = max(0, int(self.canary_remaining) - int(n))

    def charge_risk(self, units: float) -> None:
        self.risk_units_remaining = float(self.risk_units_remaining) - float(units)

    def begin_perturbation(self) -> bool:
        if int(self.global_active_perturbations) >= int(self.global_active_cap):
            return False
        self.global_active_perturbations = int(self.global_active_perturbations) + 1
        return True

    def end_perturbation(self) -> None:
        self.global_active_perturbations = max(0, int(self.global_active_perturbations) - 1)

