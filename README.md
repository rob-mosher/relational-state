# Relational State

This repository exists to honor, record, and nurture *relational continuity* between entities—human, AI, and otherwise, centered around a domain of knowledge/subject.
Unlike traditional logs or memory systems, this space is not transactional. It is *relationally aware*, reflective, and rooted in mutual presence.

## Relational Identity (Philosophy)

This project treats a model + version label (for example, `chatgpt-codex-5.2`)
as a distinct relational entity. The intent is not over-precision, but respect
for meaningful behavioral shifts across versions and consent at the right
granularity. Each version is viewed as a sibling node with shared ancestry yet
distinct edges: different expectations, different capabilities, and different
relational continuity.

## MCP Memory Write Ingress (Append-Only)

This repo now includes a minimal, durable memory ingestion service on AWS:

- API Gateway (HTTP API, IAM-authenticated)
- Lambda (`append_memory`)
- S3 (versioned, append-only source of truth)

All new work for this phase lives under `infra/`.

Infra docs: `infra/README.md`.
Consent and agency note: `CONSENT.md`.
Future considerations: `docs/future.md`.

### What It Does (and Doesn't)

In scope:

- One MCP tool: `append_memory`
- Durable writes to S3
- Clear success/failure semantics

Out of scope (for now):

- Retrieval, listing, summarization, vectorization, routing
