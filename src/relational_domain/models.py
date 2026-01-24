"""
Data models for the Relational Domain

Defines the core data structures using Pydantic for validation:
- Entry: Canonical memory entry (unchanged from engine)
- ContextEntry: Entry with relevance scores (for Context Envelope)
- ContextEnvelope: Output with provider metadata
- DomainConfig: Domain sovereignty policies and compute preferences
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Entry(BaseModel):
    """Canonical memory entry from append-only log"""

    id: str = Field(..., description="SHA-256 hash of normalized content")
    timestamp: datetime = Field(..., description="When entry was created")
    author: str = Field(..., description="Entity ID (e.g., 'claude-sonnet-4.5', 'rob-mosher')")
    type: Literal["event", "promotion", "reflection"] = Field(
        ..., description="Entry classification"
    )
    content: str = Field(..., description="Raw markdown content")
    promotion_depth: int = Field(
        default=0, ge=0, description="How many promotion levels deep (0 = original)"
    )
    trust_weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Trust score (0.0-1.0)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional: scope, source, confidence, etc."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "a7f3b2c1...",
                "timestamp": "2026-01-16T10:30:00",
                "author": "claude-sonnet-4.5",
                "type": "reflection",
                "content": "## 2026-01-16: TDD Practice...",
                "promotion_depth": 0,
                "trust_weight": 1.0,
                "metadata": {"scope": ["TileDrift", "testing"]},
            }
        }


class ContextEntry(BaseModel):
    """Entry with relevance scoring for Context Envelope"""

    entry_id: str = Field(..., description="Reference to Entry.id")
    content: str = Field(..., description="Entry content (may be truncated)")
    relevance_score: float = Field(..., ge=0.0, description="Semantic similarity score")
    final_weight: float = Field(
        ..., ge=0.0, description="After applying decay and recency boosts"
    )
    promotion_depth: int = Field(..., ge=0, description="Promotion level")
    timestamp: datetime = Field(..., description="When entry was created")
    author: str = Field(..., description="Entity ID")

    class Config:
        json_schema_extra = {
            "example": {
                "entry_id": "a7f3b2c1...",
                "content": "## 2026-01-16: TDD Practice...",
                "relevance_score": 0.87,
                "final_weight": 0.85,
                "promotion_depth": 0,
                "timestamp": "2026-01-16T10:30:00",
                "author": "claude-sonnet-4.5",
            }
        }


class ContextEnvelope(BaseModel):
    """
    Output from domain context compilation with provider transparency.
    
    Now includes provider_used to show which compute provider was negotiated.
    """

    entity_id: str = Field(..., description="Which entity's memories were queried")
    task_description: str = Field(..., description="The task/question that prompted this query")
    scope: List[str] = Field(default_factory=list, description="Scope keywords used for filtering")
    entries: List[ContextEntry] = Field(
        ..., description="Ranked entries with relevance scores"
    )
    total_tokens: int = Field(..., ge=0, description="Approximate token count")
    generated_at: datetime = Field(
        default_factory=datetime.now, description="When this envelope was created"
    )
    provider_used: Optional[str] = Field(
        default=None, description="Which provider was used for embeddings (e.g., 'local/all-MiniLM-L6-v2')"
    )
    fallback_occurred: bool = Field(
        default=False, description="Whether fallback to secondary provider occurred"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "claude-sonnet-4.5",
                "task_description": "Reflect on collaborative TDD practices",
                "scope": ["TileDrift", "testing"],
                "entries": [],
                "total_tokens": 1847,
                "generated_at": "2026-01-23T14:00:00",
                "provider_used": "local/all-MiniLM-L6-v2",
                "fallback_occurred": False,
            }
        }


class DomainConfig(BaseModel):
    """
    Domain sovereignty configuration.
    
    Separates domain policies from provider-specific configuration.
    Provider selection happens through ProviderRegistry, not here.
    """

    # Paths (domain data sovereignty)
    state_dir: str = Field(default=".relational/state/", description="Canonical log directory")
    vector_store_dir: str = Field(
        default=".relational/vector_store/", description="Vector projection storage"
    )

    # Provider preferences (for registry initialization)
    default_embedding_provider: Literal["local", "openai"] = Field(
        default="local", description="Default embedding provider (local-first)"
    )
    local_embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence-transformers model name"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key (from env or explicit)"
    )

    # Context Compilation (domain policies)
    max_context_tokens: int = Field(
        default=2000, ge=100, description="Maximum tokens in Context Envelope"
    )
    top_k_candidates: int = Field(
        default=20, ge=1, description="How many candidates to retrieve before reweighting"
    )
    strict_entity_filtering: bool = Field(
        default=True, description="Only return entity's own memories (entity-specific sovereignty)"
    )

    # Promotion (damped recursion, domain policy)
    max_promotion_depth: int = Field(default=3, ge=1, description="Hard limit on promotion levels")
    promotion_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum sigmoid probability to allow promotion",
    )
    decay_k: float = Field(
        default=2.0, gt=0.0, description="Sigmoid steepness (higher = faster decay)"
    )

    # Recency Bias (domain policy)
    recency_boost_days: int = Field(
        default=30, ge=0, description="Recent entries within N days get boost"
    )
    recency_boost_factor: float = Field(
        default=1.2, ge=1.0, description="Multiplier for recent entries"
    )

    # Trust (domain policy)
    default_trust_weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Default trust for new entries"
    )

    @classmethod
    def from_env(cls) -> "DomainConfig":
        """Load configuration with environment variable overrides"""
        config = cls()

        # Override OpenAI API key from environment if present
        if api_key := os.getenv("OPENAI_API_KEY"):
            config.openai_api_key = api_key

        # Override embedding provider if set
        if provider := os.getenv("RELATIONAL_EMBEDDING_PROVIDER"):
            if provider in ("local", "openai"):
                config.default_embedding_provider = provider  # type: ignore

        return config

    class Config:
        json_schema_extra = {
            "example": {
                "state_dir": ".relational/state/",
                "vector_store_dir": ".relational/vector_store/",
                "default_embedding_provider": "local",
                "max_context_tokens": 2000,
                "max_promotion_depth": 3,
                "decay_k": 2.0,
                "strict_entity_filtering": True,
            }
        }


# Backward compatibility alias
Config = DomainConfig
