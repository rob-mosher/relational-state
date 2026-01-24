"""FastAPI application for MCP Server.

This module implements an HTTP/SSE-based Model Context Protocol server that
orchestrates between task agents and the relational state engine.
"""
from fastapi import FastAPI, HTTPException
import uvicorn
from .models import (
    CompileContextRequest,
    CompileContextResponse,
    AppendMemoryRequest,
    AppendMemoryResponse,
    EvaluatePromotionRequest,
    EvaluatePromotionResponse,
    ListMemoriesRequest,
    ListMemoriesResponse,
    ReadMemoryRequest,
    ReadMemoryResponse,
    FilterMemoriesRequest,
    FilterMemoriesResponse,
    GetVectorStatsRequest,
    GetVectorStatsResponse,
    ExportEmbeddingsRequest,
    ExportEmbeddingsResponse,
)
from .tools import (
    compile_context_tool,
    append_memory_tool,
    evaluate_promotion_tool,
    list_memories_tool,
    read_memory_tool,
    filter_memories_tool,
    get_vector_stats_tool,
    export_embeddings_tool,
)

app = FastAPI(
    title="Relational State MCP Server",
    description="Model Context Protocol orchestration layer for Relational State Engine",
    version="0.2.0",
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-server"}


@app.post("/mcp/tools/compile_context", response_model=CompileContextResponse)
def compile_context(request: CompileContextRequest):
    """MCP Tool: Compile context envelope.

    Prepares a context envelope for an incoming agent by invoking the RLM process,
    querying the vector store, and applying weighting/decay rules.
    """
    try:
        return compile_context_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/append_memory", response_model=AppendMemoryResponse)
def append_memory(request: AppendMemoryRequest):
    """MCP Tool: Append memory entry.

    Adds a new canonical memory entry to the append-only log and triggers
    asynchronous reprojection.
    """
    try:
        return append_memory_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/evaluate_promotion", response_model=EvaluatePromotionResponse)
def evaluate_promotion(request: EvaluatePromotionRequest):
    """MCP Tool: Evaluate promotion eligibility.

    Decides whether an inference should be promoted by applying decay/hysteresis
    rules and enforcing max promotion depth.
    """
    try:
        return evaluate_promotion_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Inspection Tools
# ============================================================================


@app.post("/mcp/tools/list_memories", response_model=ListMemoriesResponse)
def list_memories(request: ListMemoriesRequest):
    """MCP Tool: List memories with pagination and filtering.

    Supports filtering by:
    - Entity/author
    - Memory type (event, promotion, reflection)
    - Promotion depth range
    - Date range

    Returns paginated results sorted by timestamp (newest first).
    """
    try:
        return list_memories_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/read_memory", response_model=ReadMemoryResponse)
def read_memory(request: ReadMemoryRequest):
    """MCP Tool: Read full memory entry by ID.

    Returns complete entry including full content and metadata.
    Returns 404 if entry ID not found.
    """
    try:
        return read_memory_tool(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/filter_memories", response_model=FilterMemoriesResponse)
def filter_memories(request: FilterMemoriesRequest):
    """MCP Tool: Advanced memory filtering.

    Supports:
    - Keyword search (OR logic)
    - Author filtering
    - Semantic search via embeddings
    - Custom metadata filters

    Returns matching entries sorted by relevance or timestamp.
    """
    try:
        return filter_memories_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/get_vector_stats", response_model=GetVectorStatsResponse)
def get_vector_stats(request: GetVectorStatsRequest):
    """MCP Tool: Get vector store statistics.

    Returns embedding model info, entry counts, and optional
    breakdown by author, type, and promotion depth.
    """
    try:
        return get_vector_stats_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/tools/export_embeddings", response_model=ExportEmbeddingsResponse)
def export_embeddings(request: ExportEmbeddingsRequest):
    """MCP Tool: Export embeddings for visualization.

    Exports embedding vectors with metadata in JSON format
    suitable for dimensionality reduction and visualization
    in external tools (UMAP, t-SNE, PCA, D3.js, etc.).
    """
    try:
        return export_embeddings_tool(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "mcp_server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
