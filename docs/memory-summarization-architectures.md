# Memory Summarization Architectures (Pre-Alpha)

This document sketches several summarization/compression approaches, from simple pass-through to more complex, trust-aware pipelines.

## Scenario A: Pass-Through (No Compression)
```mermaid
flowchart LR
  A[Model] --> B[Relational entries]
  B --> C[Context window]
```

Pros:
- Maximum fidelity
- Lowest complexity

Cons:
- Hits context limits fast
- No prioritization or dedupe

## Scenario B: Single Summarizer (Scoped Summary)
```mermaid
flowchart LR
  A[Model] --> B[Relational entries]
  B --> C[Summarizer]
  C --> D[Scoped summary]
  D --> E[Context window]
```

Pros:
- Simple and effective
- Easy to reason about

Cons:
- Single point of failure
- Loses fine-grained details

## Scenario C: Chunked Map-Reduce Summaries
```mermaid
flowchart TD
  A[Entries] --> B[Chunk by time/scope]
  B --> C[Summarize chunks]
  C --> D[Merge summaries]
  D --> E[Final summary]
```

Pros:
- Scales to long histories
- Preserves coverage across time

Cons:
- Requires chunking strategy
- Risk of summary drift

## Scenario D: Retrieval + Summarize
```mermaid
flowchart LR
  A[Entries] --> B[Index + embeddings]
  C[Query scope] --> B
  B --> D[Top-k relevant]
  D --> E[Summarize]
  E --> F[Context window]
```

Pros:
- Focused on relevance
- Efficient for large corpora

Cons:
- Requires embedding/index infra
- Recall depends on search quality

## Scenario E: Multi-Layer Memory (Hot/Warm/Cold)
```mermaid
flowchart LR
  A[New entries] --> B[Hot: raw]
  B --> C[Warm: periodic summary]
  C --> D[Cold: stable snapshot]
  D --> E[Context assembly]
```

Pros:
- Balances fidelity and scale
- Easier to keep stable anchors

Cons:
- More orchestration logic
- Needs clear refresh rules

## Scenario F: Evidence-Aware Summaries
```mermaid
flowchart LR
  A[Entries + evidence] --> B[Summarize with citations]
  B --> C[Summary + ids/hashes]
  C --> D[Context window]
```

Pros:
- Improves trust and traceability
- Enables verification on read

Cons:
- More verbose summaries
- Requires evidence discipline

## Quick Tradeoff Summary
- A is highest fidelity, lowest trust tooling.
- B/C are stable baselines for most teams.
- D/E/F add trust, scale, and traceability at higher complexity.
