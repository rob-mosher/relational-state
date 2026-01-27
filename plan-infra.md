# Prompt: Build MCP Memory Write Ingress (API Gateway + Lambda + S3)

## Goal

Implement a minimal, reliable MCP-compatible memory ingestion service on AWS.

This phase supports **ONLY memory creation (write)**.
No retrieval, no summarization, no vectorization yet.

Correctness, durability, and clear failure semantics matter more than features.

## Architecture Overview

MCP Client
  → AWS API Gateway (HTTPS, MCP-compatible endpoint)
    → AWS Lambda (stateless, synchronous)
      → Amazon S3 (durable, append-only memory store)

The system must **only acknowledge success if the memory is durably written to S3**.

---

## Scope (Strict)

IN SCOPE:
- One MCP tool: `append_memory`
- API Gateway endpoint to receive MCP tool calls
- Lambda function to validate and persist memory
- S3 as the sole source of truth
- Clear success/failure responses to caller

OUT OF SCOPE:
- Retrieval
- Listing
- Summarization
- Vector databases
- Relational routing
- Local compute
- Async pipelines

---

## MCP Interface Requirements

Expose a single MCP tool:

### Tool: append_memory

#### Request (JSON body)

```json
{
  "entity_id": "string",          // required
  "domain": "string",             // required
  "content": "string",            // required (memory text)
  "timestamp": "ISO-8601 string", // optional (server will fill if missing)
  "metadata": {                   // optional, arbitrary JSON
    "tags": ["string"],
    "source": "string",
    "confidence": 0.0
  }
}
```

#### Response (success)

```json
{
  "status": "ok",
  "memory_id": "string",
  "s3_key": "string"
}
```

#### Response (failure)

```json
{
  "status": "error",
  "error": "human-readable message"
}
```

If the memory is NOT written to S3, the response MUST be an error.

## S3 Storage Design

S3 is append-only and authoritative.

### Bucket

- Name configurable via environment variable
- Versioning ENABLED

### Object Key Format

Use a lexicographically sortable key:

```plaintext
memories/
  domain={domain}/
    entity={entity_id}/
      yyyy/mm/dd/
        {timestamp}_{uuid}.json
```

Example:

```plaintext
memories/domain=work/entity=rob/2026/01/27/2026-01-27T03-14-22Z_8f3c.json
```

This guarantees:

- Efficient prefix listing
- Natural replay order
- Zero overwrites

## Lambda Responsibilities

The Lambda function must:

1. Validate required fields
1. Normalize timestamp (UTC ISO-8601)
1. Generate a unique memory_id (UUID or ULID)
1. Construct the S3 object key
1. Write the full memory payload as JSON to S3
1. Return success ONLY after S3 confirms write
1. Memory Object Schema (stored in S3)

### Memory Object Schema (stored in S3)

```json
{
  "schema_version": 1,
  "memory_id": "uuid",
  "entity_id": "string",
  "domain": "string",
  "timestamp": "ISO-8601 string",
  "content": "string",
  "metadata": { ... }
}
```

Do NOT mutate or enrich beyond this.

## Error Handling & Reliability

- Lambda is synchronous
- If S3 putObject fails → return error
- No retries hidden from caller
- Caller is responsible for retrying on failure

The system must never claim success unless S3 write succeeded.

## Security (Minimal but Correct)

- API Gateway HTTPS only
- API key or IAM auth (simple is fine)
- No public unauthenticated access
- Entity authorization can be coarse for now

## Infrastructure-as-Code

Prefer Terraform.

Define:

- API Gateway
- Lambda
- IAM roles (least privilege)
- S3 bucket with versioning

## Non-Goals (Explicit)

- Do NOT add queues unless required
- Do NOT batch writes
- Do NOT optimize prematurely
- Do NOT add vector embeddings
- Do NOT add retrieval endpoints

## Deliverables

Terraform (or equivalent) to deploy:

1. API Gateway
   1. Lambda
   2. S3 bucket 
2. Lambda implementation (Python preferred)
3. Clear README explaining:
   1. How to call append_memory
   2. Success/failure semantics
   3. Replay guarantees

## Design Philosophy

- Append-only
- Durable over clever
- Trust comes from correctness
- Memory must never be silently lost

Build this as if it will be relied on for years.
