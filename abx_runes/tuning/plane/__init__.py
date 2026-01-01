"""
Unified Tuning Plane Router (v1.0)

Emits exactly one bundle per cycle containing:
- exploit: portfolio (applied tuning IRs)
- explore: experiments (shadow by default)

Deterministic routing + single provenance lock via content hashes.
"""

