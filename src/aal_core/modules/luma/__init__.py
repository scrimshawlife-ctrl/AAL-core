"""
LUMA — Lucid Universal Motif Animator
====================================

Canonical visualization projection layer for AAL / Abraxas symbolic state.

Key law: visualization is a deterministic projection of existing symbolic state.
It MUST NOT influence analysis or prediction.
"""

from .pipeline.export import render

__all__ = ["render"]
