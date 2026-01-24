"""Pydantic models for MCP tool requests and responses."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


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
