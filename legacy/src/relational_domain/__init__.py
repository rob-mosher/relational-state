"""
Relational Domain

A sovereign, entity-aware memory topic that owns append-only memory and
vector representations while negotiating compute providers.

Architecture:
    MCP Client → Relational Domain (sovereignty + policies)
               ↓
           Provider Registry (local/openai/anthropic...)
               ↓
           Compute (negotiated, transparent fallback)
               ↓
           Topic Data (entity-specific, append-only)

Philosophy:
    - Sovereignty: The topic owns its data and declares capabilities
    - Consent & Invitation: Compute is negotiated, never coerced
    - Entity Perspectives: Each entity (AI model or human) has its own relational space
    - Boundaries: Clear separation between topic logic and compute providers
    - Tenderness: "We're not building a brain. We're building a reflective instrument."

Each entity has sovereign memory within this topic:
    - 'claude-sonnet-4.5', 'codex-gpt-5', 'rob-mosher', etc.
    - Memories are entity-specific, kept separate by strict filtering
    - Provider selection respects entity affinity when possible
"""

__version__ = "0.6.0"
__author__ = "Rob Mosher"

from relational_domain.models import Entry, ContextEnvelope, ContextEntry, TopicConfig

__all__ = [
    "Entry",
    "ContextEnvelope",
    "ContextEntry",
    "TopicConfig",
]
