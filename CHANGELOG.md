# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **MCP Memory Inspection Tools** - 5 new MCP endpoints for memory exploration and visualization
  - `list_memories`: Paginated memory listing with filters (entity, type, promotion depth range, date range)
  - `read_memory`: Get full entry by ID with 404 handling for missing entries
  - `filter_memories`: Advanced filtering with keywords (OR logic) and semantic search via embeddings
  - `get_vector_stats`: Vector store statistics with optional breakdowns by author, type, and promotion depth
  - `export_embeddings`: Export 384-dimensional embedding vectors with metadata for external visualization (UMAP/t-SNE/PCA)
  - Comprehensive visualization guide with Python/JavaScript examples (docs/VISUALIZATION.md)
  - Enhanced vector store inspection script with grouping and statistics (scripts/inspect_vector_store.py)

## [0.2.0] - 2026-01-23

### Added

- **Relational State Engine implementation** - Complete working system with vector projections
  - Canonical log reader: Parse markdown entries from `.relational/state/` with SHA-256 IDs
  - Vector projection store: Dual embedding support (local Sentence-transformers + optional OpenAI)
  - Context compiler (RLM Agent): Semantic search with promotion decay and recency reweighting
  - Promotion logic: Damped recursion with sigmoid decay, depth limits, explicit PROMOTE decisions
  - CLI interface: `init`, `load`, `query`, `promote`, `stats`, `demo` commands via Click framework
  - Complete test suite: 45 tests passing (22 canonical log, 23 vector store)
  - Comprehensive documentation: README-ENGINE.md with installation, usage, and troubleshooting
- **Docker containerization** - Production-ready containerized deployment
  - Multi-stage Dockerfile (development + production targets)
  - docker-compose.yml with hot reloading, persistent volumes, and native logging
  - Development container pattern: Keeps sentence-transformers model warm for fast iteration
  - Named volumes for non-ephemeral storage (state + vector store)
  - JSON file logging with automatic rotation (10MB max, 3 files)
  - Resource limits to prevent memory runaway (2 CPU cores, 4GB RAM max)
  - Health checks and restart policies
  - Comprehensive Docker documentation: README-DOCKER.md with examples and troubleshooting
- Core data models with Pydantic validation (Entry, ContextEnvelope, ContextEntry, Config)
- Configuration system with environment variable support
- Token counting using tiktoken for accurate Context Envelope sizing
- Backup and restore strategies for Docker volumes
- .dockerignore for optimized build contexts
- Entrypoint script for container initialization
- **MCP Server integration** - HTTP-based Model Context Protocol orchestration layer
  - Single-container architecture: MCP server runs alongside CLI in same container
  - FastAPI application with 3 MCP tools: `compile_context`, `append_memory`, `evaluate_promotion`
  - Stateless orchestration layer that wraps existing relational engine functions
  - HTTP/SSE transport for MCP client connectivity (port 8000 exposed)
  - Hot reloading for MCP server code via Uvicorn `--reload`
  - Direct in-process access to relational engine (no network overhead)
  - Health check endpoint for monitoring
  - FastAPI automatic OpenAPI docs (Swagger UI + ReDoc)
  - Comprehensive MCP documentation: README-MCP.md with API examples and troubleshooting
  - MCP server startup script: `docker/start-mcp.sh` for container initialization
  - CLI still accessible via `docker-compose exec` while MCP server runs

### Changed

- Updated requirements.txt with ChromaDB 1.4.1 (from 0.4.22) for Python 3.12 compatibility
- Updated .gitignore with Python build artifacts (__pycache__, *.egg-info/, etc.)
- pyproject.toml with modern Python packaging and CLI entry point

## [0.1.0] - 2026-01-13

### Added

- Initial README with framing for relational state
- Relational state entry on MCP integration and cross-platform continuity
- Repo-level relational state system (.relational/)
- Documented hash-based memory architecture in relational state
- Relational state entry on global orchestration layer
- Exclude `.relational/state/**` from linting and formatting
- Add stateless relational workspace
- Exclude `.relational/stateless/**` from linting and formatting
- Add state styles and materialized view guidance

### Changed

- Merge and simplify guidance on relational state
- Balance entry guidance: recommend anchor, not too poetic, not too log-based
- Enhance directory structure guidance and add state file examples

[0.2.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.2.0
[0.1.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.1.0
