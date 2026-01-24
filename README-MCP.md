# MCP Server for Relational State Engine

HTTP-based Model Context Protocol server that orchestrates between task agents and the relational state engine.

## Architecture

The MCP server runs **in the same container** as the relational engine, providing a simple single-container architecture:

```
┌──────────────────────────────────────────────┐
│  relational container                        │
│                                              │
│  ┌─────────────────┐   ┌──────────────────┐  │
│  │  CLI (Click)    │   │  MCP Server      │  │
│  │  - init         │   │  (FastAPI)       │  │
│  │  - load         │   │  - Port 8000     │  │
│  │  - query        │   │  - HTTP/SSE API  │  │
│  │  - promote      │   │  - Hot reload    │  │
│  │  - stats        │   │                  │  │
│  └─────────────────┘   └──────────────────┘  │
│           │                     │            │
│           └──────┬──────────────┘            │
│                  │                           │
│                  ▼                           │
│       relational_engine package              │
│       - context_compiler.py                  │
│       - promotion.py                         │
│       - canonical_log.py                     │
│       - vector_store.py                      │
│       - models.py                            │
│                                              │
│  Volumes:                                    │
│  - .relational/state/                        │
│  - .relational/vector_store/                 │
└──────────────────────────────────────────────┘
           │
           ▼
External MCP Client (e.g., Claude Desktop)
http://localhost:8000/mcp/tools/compile_context
http://localhost:8000/mcp/tools/append_memory
http://localhost:8000/mcp/tools/evaluate_promotion
```

## Quick Start

```bash
# Start the container (MCP server starts automatically)
docker-compose up -d

# Check MCP server health
curl http://localhost:8000/health

# Initialize engine (first time only)
docker-compose exec relational relational init
docker-compose exec relational relational load

# Test compile_context tool
curl -X POST http://localhost:8000/mcp/tools/compile_context \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "rob-mosher",
    "task_description": "Reflect on collaborative work",
    "scope_keywords": ["TDD", "testing"],
    "target_token_budget": 4000
  }'
```

## MCP Tools

### 1. `compile_context`

Compile a context envelope for an incoming agent.

**Endpoint**: `POST /mcp/tools/compile_context`

**Request**:
```json
{
  "entity_id": "claude-sonnet-4.5",
  "task_description": "How did we approach TDD?",
  "scope_keywords": ["TDD", "testing"],
  "target_token_budget": 4000,
  "relational_posture": "exploratory"
}
```

**Response**:
```json
{
  "context_envelope": "# Context Envelope\n\n## Entry 1...",
  "confidence_notes": "Compiled 15 entries",
  "provenance_summary": {
    "total_entries": 15,
    "total_tokens": 3847,
    "decay_function": "sigmoid"
  }
}
```

### 2. `append_memory`

Append a new canonical memory entry.

**Endpoint**: `POST /mcp/tools/append_memory`

**Request**:
```json
{
  "entity_id": "rob-mosher",
  "content": "Completed MCP server integration with FastAPI",
  "memory_type": "event",
  "promotion_depth": 0
}
```

**Response**:
```json
{
  "success": true,
  "entry_id": "a1b2c3d4...",
  "message": "Entry appended to rob-mosher.md"
}
```

### 3. `evaluate_promotion`

Evaluate if an inference should be promoted.

**Endpoint**: `POST /mcp/tools/evaluate_promotion`

**Request**:
```json
{
  "entity_id": "claude-sonnet-4.5",
  "candidate_content": "TDD is most effective with small, focused tests",
  "current_promotion_depth": 0,
  "contextual_significance_score": 0.85
}
```

**Response**:
```json
{
  "decision": "ALLOW",
  "rationale": "High significance score and depth within limits",
  "suggested_depth": 1
}
```

## Development Workflow

### Hot Reloading

The MCP server supports **automatic hot reloading**:

```bash
# Edit any file in src/mcp_server/
# Uvicorn automatically reloads within 1-2 seconds

# Watch logs for reload confirmation
docker-compose logs -f

# Test changes immediately
curl http://localhost:8000/health
```

### Accessing the CLI

While the MCP server is running, you can still access the CLI:

```bash
# Any relational CLI command
docker-compose exec relational relational --help
docker-compose exec relational relational query -t "Test" -e rob-mosher
docker-compose exec relational pytest tests/ -v
```

### Viewing Logs

```bash
# Container logs (includes MCP server output)
docker-compose logs -f

# Follow specific service
docker-compose logs -f relational

# Last 100 lines
docker-compose logs --tail=100
```

## API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to explore and test MCP tools interactively in your browser.

## Usage Examples

### Compile Context for Agent

```bash
curl -X POST http://localhost:8000/mcp/tools/compile_context \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "rob-mosher",
    "task_description": "How did we implement the relational state engine?",
    "scope_keywords": ["TDD", "architecture"],
    "target_token_budget": 4000,
    "relational_posture": "exploratory"
  }' | jq '.'
```

### Append Memory

```bash
curl -X POST http://localhost:8000/mcp/tools/append_memory \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "rob-mosher",
    "content": "Successfully deployed MCP server with single-container architecture",
    "memory_type": "event",
    "promotion_depth": 0
  }' | jq '.'
```

### Evaluate Promotion

```bash
curl -X POST http://localhost:8000/mcp/tools/evaluate_promotion \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "claude-sonnet-4.5",
    "candidate_content": "Single-container MCP architecture simplifies deployment",
    "current_promotion_depth": 0,
    "contextual_significance_score": 0.8
  }' | jq '.'
```

### End-to-End Workflow

```bash
# 1. Initialize engine
docker-compose exec relational relational init
docker-compose exec relational relational load

# 2. Compile context
curl -X POST http://localhost:8000/mcp/tools/compile_context \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "rob-mosher", "task_description": "E2E test", "target_token_budget": 1000}' | jq '.provenance_summary'

# 3. Append a new memory
curl -X POST http://localhost:8000/mcp/tools/append_memory \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "test-user", "content": "E2E test complete", "memory_type": "event"}' | jq '.success'

# 4. Reload engine to pick up new entry
docker-compose exec relational relational load

# 5. Verify new entry is included in context
curl -X POST http://localhost:8000/mcp/tools/compile_context \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "test-user", "task_description": "Check", "target_token_budget": 1000}' | jq '.provenance_summary.total_entries'
```

## Troubleshooting

### MCP server won't start

```bash
# Check logs
docker-compose logs relational

# Verify container is running
docker-compose ps

# Rebuild container
docker-compose build
docker-compose up -d
```

### Port 8000 already in use

```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Map to different host port

# Restart
docker-compose down && docker-compose up -d
```

### Import errors

```bash
# Reinstall packages in container
docker-compose exec relational pip install -e /app

# Verify package installation
docker-compose exec relational pip show relational-engine
```

### Health check failing

The health check uses `curl` to check the `/health` endpoint. If it fails:

```bash
# Check if MCP server is running
docker-compose logs relational | grep "Uvicorn running"

# Manual health check
docker-compose exec relational curl http://localhost:8000/health
```

## MCP Protocol Constraints

The MCP server enforces these constraints from the specification:

- **Never mutate existing memory entries**: All operations are append-only
- **Never expose full memory history**: Only scoped context envelopes are returned
- **Treat relational state as authoritative**: MCP server never reimplements relational logic
- **Stateless across requests**: Each request is independent

## Performance Notes

### Model Warmth

The sentence-transformers model (~500MB) is loaded once when the container starts and stays warm in memory. This provides fast response times for context compilation.

### Vector Store Updates

After appending a memory via `append_memory`, you need to reload the vector store to include the new entry in context compilation:

```bash
docker-compose exec relational relational load
```

Future enhancement: Automatic background reprojection after append operations.

## Next Steps

After MCP server is working:

1. **MCP Client Integration**: Connect Claude Desktop or other MCP-compatible clients
2. **Async Reprojection**: Implement background task for vector store updates after append
3. **SSE Streaming**: Add Server-Sent Events for long-running context compilation
4. **Authentication**: Add API key or OAuth for production deployments
5. **Metrics**: Prometheus metrics for monitoring tool usage

---

**Impact Above Origin** 🤠
