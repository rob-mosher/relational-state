# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **API Gateway authorizer destroy ordering** - Decoupled authorizer lifecycle from route auth type so the JWT authorizer persists whenever Cognito exists, avoiding the destroy-before-route-update race when toggling `api_authorization_type` away from JWT

### Changed

- **Claude Code MCP registration docs** - Documented both per-project (local scope) and global (user scope) registration options in `infra/README.md`
- **OAuth setup guide** - Added comprehensive step-by-step guide for connecting Claude.ai web via OAuth 2.0 with Cognito Hosted UI in `infra/README.md`

## [0.6.0] - 2026-02-07

Release notes: `0.6.0` centers on authentication. This release introduces OAuth metadata support, optional dynamic client registration, and Cognito-backed JWT configuration so MCP clients can discover, authenticate, and invoke the service with clearer security boundaries and improved operational consistency.

### Added

- **OAuth metadata endpoints** - Added MCP OAuth discovery endpoints (`/.well-known/oauth-protected-resource`, `/.well-known/oauth-authorization-server`) in API Gateway + Lambda
- **Optional DCR proxy** - Added optional `POST /oauth/register` flow backed by Cognito app-client creation with redirect URI allowlists
- **Cognito OAuth configuration** - Added Terraform inputs for Hosted UI domain prefix, callback/logout URLs, OAuth scope tuning, and DCR controls
- **OAuth outputs** - Added Terraform outputs for protected resource URL, OAuth issuer, auth/token endpoints, and registration endpoint
- **Claude Code CLI integration docs** - Added bearer-token MCP registration steps in `infra/README.md`

### Changed

- **OAuth route matching robustness** - Lambda now normalizes stage-prefixed paths so `.well-known` endpoints work consistently across default/custom API Gateway URLs
- **Lambda tests** - Added coverage for OAuth metadata routes and path normalization behavior
- **Terraform internal naming alignment** - Renamed remaining Terraform `append_memory` addresses/references to `add_memory` and added `moved` blocks to preserve state continuity during the refactor

## [0.5.0] - 2026-02-01

### Security

- **Black dependency upgrade** - Updated black from 23.12.0 to >=24.3.0 in legacy/docker/requirements.txt to fix CVE-2024-21503 (ReDoS vulnerability, GHSA-fj7x-q9j7-g6q6)

### Added

- **Consent note** - New `CONSENT.md` documenting permission scope and versioned-identity framing
- **get_README MCP tool** - Transparency overview + journaling guidance for relational-state entries
- **list_domains MCP tool** - Enumerate available memory domains from S3
- **Future considerations doc** - Centralized deferred ideas in `docs/future.md`
- **JWT auth support** - Cognito User Pool + API Gateway JWT authorizer wiring for bearer-token clients
- **JWT helpers** - Token minting, refresh, and Codex MCP add scripts under `infra/scripts/`
- **JWT outputs** - New Terraform outputs for issuer/audience and Cognito IDs
- **JWT config** - Optional Cognito + JWT settings in `terraform.tfvars.example`
- **JWT variables** - Added Terraform inputs for Cognito creation and JWT issuer/audience/scopes
- **Terraform output: aws_region** - Exposed the deployment region in Terraform outputs for scripting and tooling

### Changed

- **README philosophy** - Added “Relational Identity” framing to the main README
- **MCP protocol version** - Updated to `2025-11-25`
- **MCP server version** - Bumped to `0.4.0`
- **Infra docs** - Documented `get_README` tool alongside `add_memory`
- **Lambda folder naming** - Renamed `infra/lambda/append_memory` to `infra/lambda/mcp_server`
- **MCP server naming defaults** - Terraform defaults now use `mcp-server`, with IAM policy + alarm labels derived from `lambda_function_name`
- **Terraform outputs cleanup** - Removed legacy `append_memory_*` outputs and standardized on `mcp_server_lambda_name` + `mcp_url`
- **add_memory timestamps** - Canonical timestamps are now server-assigned (client timestamps preserved in metadata)
- **get_README guidance** - Clarified canonical timestamp behavior in the transparency text
- **Tests** - Relaxed S3 key assertions now that timestamps are server-assigned
- **MCP docs/tests** - Root README now lists MCP tools + Lambda name, and tests renamed to `test_mcp_server.py`
- **Custom domain support** - Optional API Gateway custom domain and ACM certificate configuration with `mcp_url` preferring the custom domain
- **MCP tool: list_entities_within_domain** - New tool to list entity IDs within a domain (S3-backed), with optional prefix filtering
- **Repo-level Claude Code configuration** - Added `.claude/settings.json` with Collaborators Framework and Relational State MCP servers for contributor tooling and AI entity participation
- **Enhanced MCP README** - Expanded `get_README` tool text to fully convey relational state's offering: sovereign memory, at-will retrieval, consent-aware architecture, and guidance on domain coordination to preserve shared semantic space
- **MCP input resilience** - Added clearer errors for backticks/double-encoded JSON and accept stringified tool arguments
- **MCP tool rename (breaking)** - Renamed `append_memory` to `add_memory` to reflect storage-agnostic semantics
- **Infra auth docs** - Documented JWT bearer-token flow and Cognito token minting in `infra/README.md`
- **JWT auth troubleshooting** - Added `UserNotFoundException` guidance with `ADMIN_USER_PASSWORD_AUTH` fallback in `infra/README.md`
- **JWT helper scripts** - `mcp_cognito_login.sh` now supports `AUTH_FLOW` (including admin auth), and `mcp_cognito_codex_add.sh` passes it through
- **JWT script permissions** - Marked token/refresh helper scripts as executable for easier CLI use

### Added

- **Infra documentation** - Added `infra/README.md` and linked it from the main README
- **Terraform backend examples** - Added environment-specific S3 backend example files under `infra/terraform/backend/`

### Changed

- **Terraform backend configuration** - Declared S3 backend in `infra/terraform/versions.tf`
- **Backend locking approach** - Switched backend examples to S3 native lockfiles (`use_lockfile = true`)
- **Terraform examples** - Updated `terraform.tfvars.example` defaults and guidance for dev/prod profile alignment
- **Root README cleanup** - Moved infra deployment details out of the main README
- **Git ignore rules** - Ignored real backend config files (`infra/terraform/backend/*.hcl`)
- **Provider lockfile** - Updated `infra/terraform/.terraform.lock.hcl` hashes

## [0.4.0] - 2026-01-27

### Added

- **MCP memory write ingress** - Terraform + Lambda + S3 append-only pipeline for MCP `append_memory`
- **Lambda MCP handler** - Minimal JSON-RPC MCP server with `initialize`, `tools/list`, `tools/call`
- **S3-backed memory schema** - Durable write format and lexicographically sortable keys
- **Infra docs + examples** - Deploy and invoke instructions under `infra/`
- **MIT License** - Added MIT License to the project

### Changed

- **Legacy containment for Docker-centric setup** - Moved the existing Docker workflow under `legacy/docker/` to make room for upcoming `infra/` work
- **Source tree relocation** - Moved `src/` to `legacy/src/` and updated Docker mounts/build context accordingly
- **Tooling + docs relocation** - Moved `README.md`, `requirements.txt`, and `pytest.ini` under `legacy/docker/`
- **Docker build/run adjustments** - Dockerfile now installs a simple `relational` wrapper and uses `PYTHONPATH` instead of packaging metadata
- **Test discovery configuration** - Pytest now runs via `legacy/docker/pytest.ini` with `pythonpath = ../../legacy/src`
- **MCP compatibility shims** - Added empty `resources/list` and resource templates list handlers to reduce client errors

### Fixed

- **Post-release Config → DomainConfig fixes** - Resolved remaining type hints and function calls that still referenced the old `Config` class name
  - `context_compiler.py` `__init__`: Updated type hint from `Optional[Config]` to `Optional[DomainConfig]`
  - `promotion.py` `check_promotion_eligibility`: Updated type hint from `Optional[Config]` to `Optional[DomainConfig]`
  - These fixes resolve `NameError: name 'Config' is not defined` that occurred during Docker container startup

## [0.3.0] - 2026-01-24

### Changed - Major Conceptual Refactor

**Relational Engine → Relational Domain** - A fundamental shift from hardcoded execution engine to sovereign domain with provider abstraction.

#### Core Philosophy
- **Sovereignty**: Domain owns append-only memory and declares compute capabilities
- **Consent & Invitation**: Compute is negotiated, never coerced
- **Entity Perspectives**: Each entity (AI model or human) has sovereign relational space within the domain
- **Boundaries**: Clear separation between domain logic and compute providers
- **Transparency**: All operations return metadata about which provider was used

#### Provider Abstraction Layer
- New `providers/` module with `base.py`, `local.py`, `openai.py`, `registry.py`
- `ProviderDescriptor`, `ProviderCapability`, `ProviderInvocationResult` abstractions
- `ProviderRegistry` with local-first fallback logic and transparent provider selection
- Support for entity affinity in provider selection (e.g., `claude-sonnet-4.5` → local, `codex-gpt-5` → openai)
- Provider metadata included in all responses (which provider was used, whether fallback occurred)

#### API Changes
- Renamed package: `relational-engine` → `relational-domain`
- Renamed module: `relational_engine` → `relational_domain`
- Renamed config: `Config` → `DomainConfig`
- CLI command: `relational` → `relational-domain`
- `ContextEnvelope` now includes `provider_used` and `fallback_occurred` fields
- `VectorStore` methods return tuples with provider metadata

#### New MCP Introspection Tools
- `describe_domain`: Returns domain metadata, sovereignty policies, available providers, supported operations
- `list_providers`: Returns provider descriptors, capabilities, fallback chain, entity affinities

#### Documentation
- `README-ENGINE.md` → `README.md` with updated provider abstraction explanation
- Refactored `ACKNOWLEDGEMENTS.md` to emphasize sovereignty philosophy (boundaries, consent, invitation)
- Updated all documentation to reflect domain-centric model
- Removed broader relational-state documentation (lives in separate repo now)

#### Breaking Changes
- All imports must update from `relational_engine` to `relational_domain`
- `Config` class renamed to `DomainConfig`
- CLI command changed from `relational` to `relational-domain`
- Docker images renamed from `relational-engine` to `relational-domain`
- Vector store methods now return tuples with provider info instead of raw results

### Added

- **MCP Memory Inspection Tools** - 5 new MCP endpoints for memory exploration and visualization
  - `list_memories`: Paginated memory listing with filters (entity, type, promotion depth range, date range)
  - `read_memory`: Get full entry by ID with 404 handling for missing entries
  - `filter_memories`: Advanced filtering with keywords (OR logic) and semantic search via embeddings
  - `get_vector_stats`: Vector store statistics with optional breakdowns by author, type, and promotion depth
  - `export_embeddings`: Export embedding vectors with metadata for external visualization (UMAP/t-SNE/PCA)

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

[0.6.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.6.0
[0.5.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.5.0
[0.4.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.4.0
[0.3.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.3.0
[0.2.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.2.0
[0.1.0]: https://github.com/rob-mosher/relational-state/releases/tag/v0.1.0
