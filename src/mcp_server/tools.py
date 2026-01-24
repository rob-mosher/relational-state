"""MCP tool implementations that wrap relational engine functions."""
from datetime import datetime
from typing import Dict
from relational_engine.context_compiler import ContextCompiler
from relational_engine.vector_store import VectorStore
from relational_engine.promotion import evaluate_promotion
from relational_engine.canonical_log import (
    append_entry_to_log,
    generate_entry_id,
    load_canonical_log,
)
from relational_engine.models import Entry, Config
from .models import (
    CompileContextRequest,
    CompileContextResponse,
    AppendMemoryRequest,
    AppendMemoryResponse,
    EvaluatePromotionRequest,
    EvaluatePromotionResponse,
    ListMemoriesRequest,
    ListMemoriesResponse,
    MemorySummary,
    ReadMemoryRequest,
    ReadMemoryResponse,
    FilterMemoriesRequest,
    FilterMemoriesResponse,
    GetVectorStatsRequest,
    GetVectorStatsResponse,
    VectorStatsBreakdown,
    ExportEmbeddingsRequest,
    ExportEmbeddingsResponse,
    EmbeddingData,
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


# ============================================================================
# Memory Inspection Tools
# ============================================================================


def list_memories_tool(request: ListMemoriesRequest) -> ListMemoriesResponse:
    """MCP Tool: List memories with pagination and filtering.

    Returns paginated list of memory entries with optional filters by:
    - Entity/author
    - Memory type
    - Promotion depth range
    - Date range
    """
    # Load all entries from canonical log
    entries = load_canonical_log(state_dir="/app/.relational/state")

    # Apply filters
    filtered_entries = entries

    if request.entity_id:
        filtered_entries = [e for e in filtered_entries if e.author == request.entity_id]

    if request.memory_type:
        filtered_entries = [e for e in filtered_entries if e.type == request.memory_type]

    if request.promotion_depth_min is not None:
        filtered_entries = [
            e for e in filtered_entries if e.promotion_depth >= request.promotion_depth_min
        ]

    if request.promotion_depth_max is not None:
        filtered_entries = [
            e for e in filtered_entries if e.promotion_depth <= request.promotion_depth_max
        ]

    if request.date_from:
        filtered_entries = [e for e in filtered_entries if e.timestamp >= request.date_from]

    if request.date_to:
        filtered_entries = [e for e in filtered_entries if e.timestamp <= request.date_to]

    # Sort by timestamp descending (most recent first)
    filtered_entries.sort(key=lambda e: e.timestamp, reverse=True)

    # Total count before pagination
    total_count = len(filtered_entries)

    # Apply pagination
    start = request.offset
    end = start + request.limit
    page_entries = filtered_entries[start:end]

    # Convert to summaries
    summaries = [
        MemorySummary(
            id=entry.id,
            timestamp=entry.timestamp,
            author=entry.author,
            type=entry.type,
            promotion_depth=entry.promotion_depth,
            trust_weight=entry.trust_weight,
            content_preview=entry.content[:200] + ("..." if len(entry.content) > 200 else ""),
        )
        for entry in page_entries
    ]

    # Build filters summary
    filters_applied = {
        "entity_id": request.entity_id,
        "memory_type": request.memory_type,
        "promotion_depth_min": request.promotion_depth_min,
        "promotion_depth_max": request.promotion_depth_max,
        "date_from": request.date_from.isoformat() if request.date_from else None,
        "date_to": request.date_to.isoformat() if request.date_to else None,
    }

    return ListMemoriesResponse(
        entries=summaries,
        total_count=total_count,
        offset=request.offset,
        limit=request.limit,
        filters_applied=filters_applied,
    )


def read_memory_tool(request: ReadMemoryRequest) -> ReadMemoryResponse:
    """MCP Tool: Read full memory entry by ID.

    Retrieves complete entry including full content and metadata.
    Raises ValueError if entry ID not found.
    """
    config = Config.from_env()
    vector_store = VectorStore(config=config)

    # Query ChromaDB for specific ID
    result = vector_store.collection.get(ids=[request.entry_id], include=["documents", "metadatas"])

    if not result["ids"] or len(result["ids"]) == 0:
        raise ValueError(f"Entry not found: {request.entry_id}")

    # Extract data
    entry_id = result["ids"][0]
    content = result["documents"][0]
    metadata = result["metadatas"][0]

    # Build response
    return ReadMemoryResponse(
        id=entry_id,
        timestamp=datetime.fromisoformat(metadata["timestamp"]),
        author=metadata["author"],
        type=metadata["type"],
        content=content,
        promotion_depth=metadata["promotion_depth"],
        trust_weight=metadata["trust_weight"],
        metadata={
            k.replace("meta_", ""): v for k, v in metadata.items() if k.startswith("meta_")
        },
    )


def filter_memories_tool(request: FilterMemoriesRequest) -> FilterMemoriesResponse:
    """MCP Tool: Advanced filtering with semantic search and keywords.

    Supports:
    - Keyword search (OR logic)
    - Author filtering
    - Semantic search via embeddings
    - Custom metadata filters
    """
    config = Config.from_env()

    # Use semantic search if query provided
    if request.semantic_query:
        vector_store = VectorStore(config=config)
        results = vector_store.query(
            query_text=request.semantic_query,
            entity_id=request.author,
            top_k=request.limit,
        )

        # Convert to Entry list
        entries = [entry for entry, score in results]

    else:
        # Load from canonical log
        entries = load_canonical_log(state_dir="/app/.relational/state")

        # Apply author filter
        if request.author:
            entries = [e for e in entries if e.author == request.author]

        # Apply keyword filter (OR logic - any keyword matches)
        if request.keywords:
            filtered = []
            for entry in entries:
                content_lower = entry.content.lower()
                if any(kw.lower() in content_lower for kw in request.keywords):
                    filtered.append(entry)
            entries = filtered

        # Apply metadata filters
        if request.metadata_filters:
            filtered = []
            for entry in entries:
                matches = True
                for key, value in request.metadata_filters.items():
                    if entry.metadata.get(key) != value:
                        matches = False
                        break
                if matches:
                    filtered.append(entry)
            entries = filtered

        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        # Limit results
        entries = entries[: request.limit]

    # Convert to summaries
    summaries = [
        MemorySummary(
            id=entry.id,
            timestamp=entry.timestamp,
            author=entry.author,
            type=entry.type,
            promotion_depth=entry.promotion_depth,
            trust_weight=entry.trust_weight,
            content_preview=entry.content[:200] + ("..." if len(entry.content) > 200 else ""),
        )
        for entry in entries
    ]

    search_metadata = {
        "semantic_query_used": request.semantic_query is not None,
        "keywords_used": request.keywords,
        "author_filter": request.author,
        "metadata_filters": request.metadata_filters,
    }

    return FilterMemoriesResponse(
        entries=summaries,
        total_count=len(summaries),
        search_metadata=search_metadata,
    )


def get_vector_stats_tool(request: GetVectorStatsRequest) -> GetVectorStatsResponse:
    """MCP Tool: Get vector store statistics.

    Returns:
    - Total entry count
    - Authors list
    - Embedding provider/model info
    - Optional: Breakdown by author, type, promotion depth
    """
    config = Config.from_env()
    vector_store = VectorStore(config=config)

    # Get base stats
    stats = vector_store.get_stats()

    breakdown = None
    if request.include_breakdown and stats["total_entries"] > 0:
        # Get all entries for breakdown
        all_results = vector_store.collection.get(include=["metadatas"])

        # Count by author, type, and promotion depth
        by_author: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_promotion_depth: Dict[int, int] = {}

        for metadata in all_results["metadatas"]:
            # By author
            author = metadata["author"]
            by_author[author] = by_author.get(author, 0) + 1

            # By type
            mem_type = metadata["type"]
            by_type[mem_type] = by_type.get(mem_type, 0) + 1

            # By promotion depth
            depth = metadata["promotion_depth"]
            by_promotion_depth[depth] = by_promotion_depth.get(depth, 0) + 1

        breakdown = VectorStatsBreakdown(
            by_author=by_author, by_type=by_type, by_promotion_depth=by_promotion_depth
        )

    return GetVectorStatsResponse(
        total_entries=stats["total_entries"],
        authors=stats["authors"],
        embedding_provider=stats["embedding_provider"],
        embedding_model=stats["embedding_model"],
        embedding_dim=stats["embedding_dim"],
        breakdown=breakdown,
    )


def export_embeddings_tool(request: ExportEmbeddingsRequest) -> ExportEmbeddingsResponse:
    """MCP Tool: Export embeddings for external visualization.

    Exports embedding vectors with metadata for dimensionality reduction
    and visualization in external tools (UMAP, t-SNE, PCA, etc.).

    Returns JSON-serializable format suitable for:
    - Python notebooks (sklearn, umap-learn)
    - JavaScript (D3.js, Observable)
    - BI tools (Tableau, etc.)
    """
    config = Config.from_env()
    vector_store = VectorStore(config=config)

    # Build query filters
    where_filter = None
    if request.entity_id:
        where_filter = {"author": request.entity_id}

    # Get entries with embeddings
    result = vector_store.collection.get(
        where=where_filter,
        limit=request.max_entries,
        include=["embeddings", "documents", "metadatas"],
    )

    if not result["ids"] or len(result["ids"]) == 0:
        # Return empty result
        return ExportEmbeddingsResponse(
            embeddings=[],
            total_exported=0,
            embedding_dim=vector_store.embedding_dim,
            notes="No entries found matching filters",
        )

    # Build embedding data
    embedding_data = []
    for i in range(len(result["ids"])):
        entry_id = result["ids"][i]
        embedding = result["embeddings"][i]
        content = result["documents"][i]
        metadata = result["metadatas"][i]

        embedding_data.append(
            EmbeddingData(
                id=entry_id,
                embedding=embedding,
                author=metadata["author"],
                type=metadata["type"],
                timestamp=datetime.fromisoformat(metadata["timestamp"]),
                promotion_depth=metadata["promotion_depth"],
                content_preview=content[:200] + ("..." if len(content) > 200 else ""),
            )
        )

    notes = (
        f"Exported {len(embedding_data)} embeddings with dimension {vector_store.embedding_dim}. "
        "Use UMAP, t-SNE, or PCA for dimensionality reduction to 2D/3D. "
        "Example (Python): "
        "import umap; reducer = umap.UMAP(n_components=2); "
        "coords = reducer.fit_transform([e['embedding'] for e in embeddings])"
    )

    return ExportEmbeddingsResponse(
        embeddings=embedding_data,
        total_exported=len(embedding_data),
        embedding_dim=vector_store.embedding_dim,
        notes=notes,
    )
