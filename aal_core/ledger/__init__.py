"""
Append-only evidence ledger.

Used by governance/execution paths to produce durable, audit-friendly receipts.
"""
from __future__ import annotations

from .ledger import EvidenceLedger

__all__ = ["EvidenceLedger"]
