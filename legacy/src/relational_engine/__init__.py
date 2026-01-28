"""
Relational State Engine

A lightweight system for maintaining entity-specific relational memory using
canonical append-only logs and vector projections, with controlled promotion logic.

Architecture:
    Request → RLM Agent (Context Compilation) → Context Envelope → Enacting Agent
    Ephemeral reasoning by default, with damped recursive promotion

Philosophy:
    - Agency & Choice: Models query voluntarily
    - Entity-Specific Continuity: Distinct histories per entity
    - Reflective Instrument: "We're not building a brain"
    - Impact Above Origin: Focus on contribution, not origin
"""

__version__ = "0.4.0"
__author__ = "Rob Mosher"

from relational_engine.models import Entry, ContextEnvelope, ContextEntry, Config

__all__ = [
    "Entry",
    "ContextEnvelope",
    "ContextEntry",
    "Config",
]
