"""Pydantic models for MCP tool requests and responses."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


class CompileContextRequest(BaseModel):
    """Request model for compile_context MCP tool."""
    entity_id: str = Field(..., description="Model + version identifier")
    task_description: str = Field(..., description="Task description for context compilation")
    scope_keywords: Optional[List[str]] = Field(default=None, description="Optional scope filters")
    target_token_budget: int = Field(default=4000, description="Target token budget")
    relational_posture: str = Field(default="exploratory", description="exploratory or executional")


class CompileContextResponse(BaseModel):
    """Response model for compile_context MCP tool."""
    context_envelope: str = Field(..., description="Compiled context as string")
    confidence_notes: Optional[str] = Field(default=None, description="Confidence metadata")
    provenance_summary: dict = Field(..., description="Counts, not content")


class AppendMemoryRequest(BaseModel):
    """Request model for append_memory MCP tool."""
    entity_id: str
    content: str
    memory_type: Literal["event", "promotion", "reflection"]
    promotion_depth: int = Field(default=0)


class AppendMemoryResponse(BaseModel):
    """Response model for append_memory MCP tool."""
    success: bool
    entry_id: str
    message: str


class EvaluatePromotionRequest(BaseModel):
    """Request model for evaluate_promotion MCP tool."""
    entity_id: str
    candidate_content: str
    current_promotion_depth: int
    contextual_significance_score: float = Field(ge=0.0, le=1.0)


class EvaluatePromotionResponse(BaseModel):
    """Response model for evaluate_promotion MCP tool."""
    decision: Literal["ALLOW", "DENY"]
    rationale: str
    suggested_depth: Optional[int] = None


# ============================================================================
# Memory Inspection Tools Models
# ============================================================================


class ListMemoriesRequest(BaseModel):
    """Request model for list_memories MCP tool."""
    entity_id: Optional[str] = Field(default=None, description="Filter by author/entity ID")
    memory_type: Optional[str] = Field(default=None, description="Filter by type: event, promotion, or reflection")
    promotion_depth_min: Optional[int] = Field(default=None, ge=0, description="Minimum promotion depth (inclusive)")
    promotion_depth_max: Optional[int] = Field(default=None, ge=0, description="Maximum promotion depth (inclusive)")
    date_from: Optional[datetime] = Field(default=None, description="Start date for filtering (inclusive)")
    date_to: Optional[datetime] = Field(default=None, description="End date for filtering (inclusive)")
    limit: int = Field(default=50, ge=1, le=500, description="Number of results per page")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class MemorySummary(BaseModel):
    """Summary of a memory entry (without full content)."""
    id: str
    timestamp: datetime
    author: str
    type: str
    promotion_depth: int
    trust_weight: float
    content_preview: str = Field(..., description="First 200 characters of content")


class ListMemoriesResponse(BaseModel):
    """Response model for list_memories MCP tool."""
    entries: List[MemorySummary]
    total_count: int = Field(..., description="Total entries matching filters (for pagination)")
    offset: int
    limit: int
    filters_applied: Dict[str, Any] = Field(..., description="Summary of filters used")


class ReadMemoryRequest(BaseModel):
    """Request model for read_memory MCP tool."""
    entry_id: str = Field(..., description="Entry ID (SHA-256 hash)")


class ReadMemoryResponse(BaseModel):
    """Response model for read_memory MCP tool."""
    id: str
    timestamp: datetime
    author: str
    type: str
    content: str
    promotion_depth: int
    trust_weight: float
    metadata: Dict[str, Any]


class FilterMemoriesRequest(BaseModel):
    """Request model for filter_memories MCP tool (advanced filtering)."""
    keywords: Optional[List[str]] = Field(default=None, description="Keywords to search for in content (OR logic)")
    author: Optional[str] = Field(default=None, description="Filter by author")
    semantic_query: Optional[str] = Field(default=None, description="Semantic search query using embeddings")
    metadata_filters: Optional[Dict[str, Any]] = Field(default=None, description="Custom metadata key-value filters")
    limit: int = Field(default=50, ge=1, le=500)


class FilterMemoriesResponse(BaseModel):
    """Response model for filter_memories MCP tool."""
    entries: List[MemorySummary]
    total_count: int
    search_metadata: Dict[str, Any] = Field(..., description="Details about the search performed")


class GetVectorStatsRequest(BaseModel):
    """Request model for get_vector_stats MCP tool."""
    include_breakdown: bool = Field(default=True, description="Include detailed breakdown by author and type")


class VectorStatsBreakdown(BaseModel):
    """Breakdown statistics by author or type."""
    by_author: Dict[str, int] = Field(..., description="Entry counts per author")
    by_type: Dict[str, int] = Field(..., description="Entry counts per type")
    by_promotion_depth: Dict[int, int] = Field(..., description="Entry counts per promotion depth")


class GetVectorStatsResponse(BaseModel):
    """Response model for get_vector_stats MCP tool."""
    total_entries: int
    authors: List[str]
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
    breakdown: Optional[VectorStatsBreakdown] = None


class ExportEmbeddingsRequest(BaseModel):
    """Request model for export_embeddings MCP tool."""
    entity_id: Optional[str] = Field(default=None, description="Filter by author (for entity-specific visualization)")
    max_entries: int = Field(default=1000, ge=1, le=5000, description="Maximum number of entries to export")
    include_metadata: bool = Field(default=True, description="Include entry metadata (author, type, timestamp)")


class EmbeddingData(BaseModel):
    """Single entry embedding with metadata."""
    id: str
    embedding: List[float]
    author: str
    type: str
    timestamp: datetime
    promotion_depth: int
    content_preview: str


class ExportEmbeddingsResponse(BaseModel):
    """Response model for export_embeddings MCP tool."""
    embeddings: List[EmbeddingData]
    total_exported: int
    embedding_dim: int
    export_timestamp: datetime = Field(default_factory=datetime.now)
    notes: str = Field(..., description="Usage notes for visualization")


# Domain Introspection Tools (v0.4.0)

class DescribeDomainRequest(BaseModel):
    """Request model for describe_domain introspection tool."""
    include_provider_status: bool = Field(default=True, description="Include current provider availability")


class ProviderInfo(BaseModel):
    """Provider information for describe_domain response."""
    name: str
    type: str
    available: bool
    capabilities: List[str]
    requires_credentials: bool
    embedding_dimensions: Optional[int] = None


class DescribeDomainResponse(BaseModel):
    """Response model for describe_domain introspection tool."""
    domain_version: str
    sovereignty_policies: Dict[str, Any]
    available_operations: List[str]
    providers: List[ProviderInfo]
    provider_preference_order: List[str]
    strict_entity_filtering: bool
    max_context_tokens: int
    max_promotion_depth: int


class ListProvidersRequest(BaseModel):
    """Request model for list_providers introspection tool."""
    capability_filter: Optional[str] = Field(default=None, description="Filter by capability (embed, summarize, etc.)")


class ListProvidersResponse(BaseModel):
    """Response model for list_providers introspection tool."""
    providers: List[ProviderInfo]
    fallback_chain: List[str]
    entity_affinities: Dict[str, str]
