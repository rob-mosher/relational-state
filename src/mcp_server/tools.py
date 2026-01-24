"""MCP tool implementations that wrap relational engine functions."""
from datetime import datetime
from relational_engine.context_compiler import ContextCompiler
from relational_engine.vector_store import VectorStore
from relational_engine.promotion import evaluate_promotion
from relational_engine.canonical_log import append_entry_to_log, generate_entry_id
from relational_engine.models import Entry, Config
from .models import (
    CompileContextRequest,
    CompileContextResponse,
    AppendMemoryRequest,
    AppendMemoryResponse,
    EvaluatePromotionRequest,
    EvaluatePromotionResponse,
)


def compile_context_tool(request: CompileContextRequest) -> CompileContextResponse:
    """MCP Tool: Compile context envelope for an agent.

    Invokes the RLM process to prepare a context envelope by querying the vector store
    and applying weighting/decay rules.
    """
    # Initialize vector store and context compiler
    config = Config.from_env()
    vector_store = VectorStore(config=config)
    compiler = ContextCompiler(vector_store=vector_store, config=config)

    envelope = compiler.compile_context(
        task_description=request.task_description,
        entity_id=request.entity_id,
        scope=request.scope_keywords,
        decay_function="sigmoid",
    )

    # Format context envelope as markdown
    markdown_parts = [
        f"# Context Envelope for {envelope.entity_id}",
        f"\n**Task**: {envelope.task_description}",
        f"**Generated**: {envelope.generated_at}",
        f"**Total Tokens**: {envelope.total_tokens}",
        f"**Entries**: {len(envelope.entries)}\n",
    ]

    for i, ctx_entry in enumerate(envelope.entries, 1):
        markdown_parts.append(f"\n## Entry {i}")
        markdown_parts.append(f"**Relevance Score**: {ctx_entry.relevance_score:.4f}")
        markdown_parts.append(f"**Final Weight**: {ctx_entry.final_weight:.4f}")
        markdown_parts.append(f"**Author**: {ctx_entry.author}")
        markdown_parts.append(f"**Promotion Depth**: {ctx_entry.promotion_depth}")
        markdown_parts.append(f"**Date**: {ctx_entry.timestamp}")
        markdown_parts.append(f"\n{ctx_entry.content}\n")

    context_envelope_str = "\n".join(markdown_parts)

    return CompileContextResponse(
        context_envelope=context_envelope_str,
        confidence_notes=f"Compiled {len(envelope.entries)} entries",
        provenance_summary={
            "total_entries": len(envelope.entries),
            "total_tokens": envelope.total_tokens,
            "decay_function": "sigmoid",
        },
    )


def append_memory_tool(request: AppendMemoryRequest) -> AppendMemoryResponse:
    """MCP Tool: Append a new canonical memory entry.

    Adds a new entry to the append-only canonical log. The entry will be
    picked up by the next vector store reprojection.
    """
    entry = Entry(
        id="",  # Will be generated below
        timestamp=datetime.now(),
        author=request.entity_id,
        type=request.memory_type,
        content=request.content,
        promotion_depth=request.promotion_depth,
        trust_weight=1.0,
        metadata={},
    )

    entry.id = generate_entry_id(entry.content)
    append_entry_to_log(entry, state_dir="/app/.relational/state")

    return AppendMemoryResponse(
        success=True,
        entry_id=entry.id,
        message=f"Entry appended to {request.entity_id}.md",
    )


def evaluate_promotion_tool(request: EvaluatePromotionRequest) -> EvaluatePromotionResponse:
    """MCP Tool: Evaluate if an inference should be promoted.

    Applies decay/hysteresis rules and enforces max promotion depth to decide
    whether an inference should be promoted to the canonical log.
    """
    entry = Entry(
        id="temp",
        timestamp=datetime.now(),
        author=request.entity_id,
        type="event",
        content=request.candidate_content,
        promotion_depth=request.current_promotion_depth,
        trust_weight=request.contextual_significance_score,
        metadata={},
    )

    config = Config.from_env()
    decision = evaluate_promotion(entry=entry, reason="MCP evaluation request", config=config)

    return EvaluatePromotionResponse(
        decision="ALLOW" if decision.allowed else "DENY",
        rationale=decision.reason,
        suggested_depth=(
            request.current_promotion_depth + 1 if decision.allowed else None
        ),
    )
