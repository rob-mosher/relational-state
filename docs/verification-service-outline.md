# Relational Verification Service Outline (Pre-Alpha)

This is a lightweight blueprint for a service that validates, scores, and serves relational-state entries with verifiable provenance.
Storage and verification are intentionally decoupled: memories can live anywhere, while one or more verification sources attest to their authenticity.

## Goals
- Verify integrity (content hash) and provenance (signature).
- Provide scoped retrieval with trust-aware ranking.
- Keep the system minimal and auditable.
- Support centralized or distributed verification without binding to a single storage backend.

## Non-Goals
- Long-term storage design decisions (vendor-specific).
- Encryption at rest (can be layered later).
- Complex consensus or multi-party approval flows.

## Inputs
- Entry submission (content + metadata + signature).
- Query requests (scope + filters + trust thresholds).

## Outputs
- Verification result (pass/fail + reasons).
- Trust score + tier.
- Ranked entries for a scope.
- Optional summary of verified entries.

## Core Components
1. Ingest API
   - Accept entry payloads.
   - Enforce schema and size limits.
2. Verification Pipeline
   - Normalize content.
   - Compute hash and compare to provided id.
   - Verify signature (kid + sig).
3. Append-Only Log
   - Maintain Merkle log and root.
   - Provide proofs for entries.
4. Storage
   - Entry store (content + metadata) or external pointers.
   - Log store (roots + proofs) can be separate from content storage.
5. Retrieval API
   - Query by scope and filters.
   - Return entries + verification status + scores.
6. Scoring Engine
   - Compute trust score from signals.
7. Summarizer (optional)
   - Summarize only verified entries.
8. Audit + Metrics
   - Track verification failures, replay, and query volume.

## Minimal Data Flow
1. Client submits entry -> Ingest API.
2. Verification Pipeline checks schema, hash, signature.
3. Entry is appended to log -> Merkle root updated.
4. Entry + proof stored (or log stores proofs for externally stored content).
5. Retrieval API verifies and ranks entries on read.

## Suggested Endpoints
- POST /entries
  - Body: entry payload
  - Response: verification status + id + log root
- GET /entries?repo=&issue=&branch=&since=
  - Response: entries + scores + verification flags
- GET /entries/{id}
  - Response: entry + proof
- GET /log/roots/{root}
  - Response: proof bundle
- GET /attestations/{id}
  - Response: third-party attestations for a given hash

## Verification Steps (Write)
1. Normalize content (line endings, trim trailing spaces).
2. Compute hash -> match id.
3. Verify signature against kid.
4. Validate schema (required/optional fields).
5. Append to Merkle log and persist proof, independent of content storage.

## Trust Scoring (Example)
Signals:
- Signature verified
- Hash matches content
- Log proof verified
- Evidence presence (commit/file)
- Recency window
- Source tier (Observed/Inferred/Assumed)

Score -> Tier:
- Verified / Likely / Tentative

## Security Considerations
- OIDC short-lived tokens for write access.
- Rate limiting for ingest and query.
- Scope enforcement (repo-level ACLs).
- Replay protection (idempotent writes by hash).
- Trust policy: readers define which attesters/logs they accept.

## Failure Modes
- Invalid signature: reject (400).
- Hash mismatch: reject (400).
- Log append failure: reject (500).
- Schema failure: reject (400).
- Verification on read fails: mark as unverified, exclude from summaries.

## MVP Checklist
- Schema validation + hash verification.
- Signature verification (single keypair).
- Merkle log append + proof storage.
- Scoped query with trust score.
