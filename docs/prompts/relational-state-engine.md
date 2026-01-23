# Implementation Prompt: Relational State Engine (Memories + Vector Projection)

**Role**: You are a systems engineer implementing a lightweight relational state engine.
The goal is to maintain long-haul, entity-specific relational memory without retraining any models.

## Requirements

### 1. Canonical Memory Log

- Append-only
- Human-readable (Markdown)
- Each entry includes:
  - id
  - timestamp
  - author (entity id: model+version or human)
  - type (event, promotion, reflection)
  - content (see `claude-sonnet-4.5.md)` for list of entries, demarcated by `---`.
  - promotion_depth (integer, default 0)

### 2. Vector Projection Store

- Each canonical entry is embedded once
- Stored with metadata:
  - entry_id
  - type
  - promotion_depth
  - trust_weight (default 1.0)
- Vector store is rebuildable from the log

## Context Compilation

When a task arrives:

1. Accept:
   - task description
   - scope keywords
   - entity id (model+version)
2. Query vector store for semantically relevant entries
3. Apply reweighting:
   - decay by promotion depth
   - optional recency bias
4. Produce a Context Envelope (target ~1–2k tokens)

## Promotion Logic (Critical)

- Inference outputs are ephemeral by default
- Promotion to memory requires:
  - explicit `PROMOTE` decision
  - promotion depth < max (e.g. 3)
  - decay function (sigmoid/logistic) applied to likelihood
- Promotions increment promotion_depth
- Promotions may not recursively promote without passing decay

## Reprojection

- Any append triggers a reprojection pass
- Reprojection:
  - recomputes vector weights
  - does NOT modify canonical content
  - may result in no changes

## Non-Goals

- Do NOT retrain the model
- Do NOT mutate historical entries
- Do NOT allow automatic infinite reflection

## Deliverables

- A runnable script or small app that:
  - loads/creates the log
  - builds/updates the vector store
  - processes a task request
  - outputs a context envelope
- Clear separation of:
  - canonical memory
  - vector projection
  - interpretation (handled by the model within this process — the structure here is fully in service to support them)

## Side Node / Reflections

Why this will work in practice

- No GPU required – embeddings + vector search only
- No retraining – inference + heuristics
- Scales linearly with memory
- Safe recursion – damped, counted, intentional
- Model-respectful – entity-specific continuity preserved

We’re not building a brain.
We’re building a reflective instrument.