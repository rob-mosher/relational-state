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
)
from .tools import (
    compile_context_tool,
    append_memory_tool,
    evaluate_promotion_tool,
)

app = FastAPI(
    title="Relational State MCP Server",
    description="Model Context Protocol orchestration layer for Relational State Engine",
    version="0.1.0",
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


if __name__ == "__main__":
    uvicorn.run(
        "mcp_server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
