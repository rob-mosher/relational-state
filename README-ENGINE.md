# Relational State Engine

**A lightweight, runnable demonstration of entity-specific relational memory using canonical append-only logs and vector projections, with controlled promotion logic.**

> **Philosophy**: *"We're not building a brain. We're building a reflective instrument."*

## Overview

The Relational State Engine implements the architecture described in `docs/prompts/relational-state-engine.md`, enabling:

- **Entity-specific continuity**: Separate memory streams for each collaborator (AI or human)
- **Semantic search**: Find relevant memories using vector embeddings
- **Promotion with decay**: Controlled recursive reflection with damped promotion
- **No GPU required**: Local embeddings (Sentence-transformers) or optional OpenAI
- **Rebuildable**: Vector store can be regenerated from canonical log

## Architecture

```
Request → RLM Agent (Context Compilation) → Context Envelope → Enacting Agent
          ↓                                                          ↓
    Vector Store                                            Ephemeral Reasoning
                                                                     ↓
                                                          Significant Event?
                                                                     ↓
Stable State ← Discard ← Promotion Check ← Reprojection ← Append Memory
                              ↑________________↓
                           (damped recursion)
```

**Key Insight**: Most inference is ephemeral. Only significant events get appended. Promotion is controlled by depth limits and decay functions.

## Installation

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)

### Setup

```bash
# Clone or navigate to repository
cd rm-relational-state

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

### Optional: OpenAI Embeddings

For higher quality embeddings (requires API key):

```bash
pip install openai
export OPENAI_API_KEY="your-api-key"
export RELATIONAL_EMBEDDING_PROVIDER="openai"
```

## Quick Start

### 1. Initialize

```bash
relational init
```

### 2. Load Entries

```bash
# Load and embed entries from .relational/state/
relational load

# Or rebuild from scratch
relational load --rebuild
```

### 3. Query for Context

```bash
relational query \
  --task "Reflect on collaborative TDD practices" \
  --entity claude-sonnet-4.5 \
  --scope TDD --scope testing
```

### 4. Check Statistics

```bash
relational stats
```

### 5. Run Demo

```bash
relational demo
```

## CLI Reference

### `relational init`

Initialize the vector store.

**Options**: None

**Example**:
```bash
relational init
```

---

### `relational load`

Load entries from canonical log and embed them.

**Options**:
- `--rebuild`: Rebuild vector store from scratch (default: upsert)

**Examples**:
```bash
# Incremental update
relational load

# Full rebuild
relational load --rebuild
```

---

### `relational query`

Query for a context envelope.

**Options**:
- `--task, -t`: Task description (required)
- `--entity, -e`: Entity ID (required) e.g., `claude-sonnet-4.5`, `rob-mosher`
- `--scope, -s`: Scope keywords (optional, can specify multiple)
- `--decay`: Decay function - `sigmoid` (default) or `linear`

**Examples**:
```bash
# Simple query
relational query \
  --task "How did we approach test-driven development?" \
  --entity claude-sonnet-4.5

# With scope filtering
relational query \
  --task "Reflect on UI design decisions" \
  --entity claude-sonnet-4.5 \
  --scope TileDrift --scope UX

# With linear decay
relational query \
  --task "Architecture decisions" \
  --entity rob-mosher \
  --decay linear
```

---

### `relational promote`

Promote an entry to memory (with decay check).

**Options**:
- `--entry-id`: Entry ID to promote (required, can be partial)
- `--reason`: Reason for promotion (required)

**Example**:
```bash
relational promote \
  --entry-id a7f3b2c1 \
  --reason "Core architectural insight about promotion logic"
```

---

### `relational stats`

Show vector store statistics.

**Example**:
```bash
relational stats
```

---

### `relational demo`

Run end-to-end demonstration workflow.

**Example**:
```bash
relational demo
```

## Configuration

Configuration can be set via environment variables or modified in `Config` class:

### Environment Variables

```bash
# Embedding provider (local or openai)
export RELATIONAL_EMBEDDING_PROVIDER="local"

# OpenAI API key (if using openai provider)
export OPENAI_API_KEY="sk-..."

# State directory (default: .relational/state/)
# Vector store directory (default: .relational/vector_store/)
```

### Config Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `state_dir` | `.relational/state/` | Canonical log directory |
| `vector_store_dir` | `.relational/vector_store/` | Vector projections storage |
| `embedding_provider` | `local` | `local` or `openai` |
| `local_embedding_model` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `openai_embedding_model` | `text-embedding-3-small` | OpenAI model |
| `max_context_tokens` | `2000` | Token limit for Context Envelope |
| `top_k_candidates` | `20` | Candidates before reweighting |
| `strict_entity_filtering` | `True` | Entity-specific continuity |
| `max_promotion_depth` | `3` | Hard limit on promotion levels |
| `promotion_threshold` | `0.3` | Minimum sigmoid probability |
| `decay_k` | `2.0` | Sigmoid steepness (higher = faster decay) |
| `recency_boost_days` | `30` | Recent entries boost window |
| `recency_boost_factor` | `1.2` | Multiplier for recent entries |

## Canonical Log Format

Entries are stored as markdown files in `.relational/state/`:

```markdown
## 2026-01-16: Entry Title

Entry content here.

Paragraphs, lists, code blocks, etc.

---

## 2026-01-17: Another Entry

More content...

---
```

### Entry Structure (Parsed)

- **ID**: SHA-256 hash of normalized content
- **Timestamp**: Extracted from `## YYYY-MM-DD: Title` header
- **Author**: Derived from filename (`claude-sonnet-4.5.md` → `claude-sonnet-4.5`)
- **Type**: `event`, `promotion`, or `reflection` (inferred from keywords)
- **Content**: Raw markdown
- **Promotion Depth**: `0` for original entries, incremented on promotion
- **Trust Weight**: Default `1.0`

## Promotion Logic

Promotion follows **damped recursion** to prevent infinite reflection:

### Decision Flow

1. **Is this a promotion candidate?** (Manual decision by user/agent)
2. **If yes → Evaluate:**
   - Check `promotion_depth < MAX_DEPTH` (default: 3)
   - Calculate promotion probability: `sigmoid(-depth * k)`
   - If `probability > threshold` (default: 0.3):
     - **ALLOWED**: Create new entry with `depth+1`, append to log
     - Trigger reprojection
   - Else: **BLOCKED** (stays ephemeral)
3. **If no → Discard** (ephemeral)

### Decay Functions

**Sigmoid (default)**:
```
decay = 1 / (1 + exp(k * depth))
```
- depth=0 → 1.0 (no decay)
- depth=1 → 0.12 (significant decay)
- depth=2 → 0.02 (heavy decay)
- depth=3 → 0.002 (nearly eliminated)

**Linear**:
```
decay = max(0, 1 - 0.33 * depth)
```

### Check Eligibility (Without Promoting)

```python
from relational_engine.canonical_log import load_canonical_log
from relational_engine.promotion import check_promotion_eligibility

entries = load_canonical_log()
entry = entries[0]

eligibility = check_promotion_eligibility(entry)
print(f"Eligible: {eligibility['eligible']}")
print(f"Probability: {eligibility['probability']:.3f}")
print(f"Reason: {eligibility['reason']}")
```

## Programmatic Usage

### Load and Query

```python
from relational_engine.canonical_log import load_canonical_log
from relational_engine.vector_store import VectorStore
from relational_engine.context_compiler import ContextCompiler
from relational_engine.models import Config

# Initialize
config = Config.from_env()
entries = load_canonical_log(config.state_dir)

# Build vector store
vector_store = VectorStore(config=config)
vector_store.embed_entries(entries)

# Compile context
compiler = ContextCompiler(vector_store, config=config)
envelope = compiler.compile_context(
    task_description="Reflect on test-driven development",
    entity_id="claude-sonnet-4.5",
    scope=["TDD", "testing"]
)

# Use the context
print(f"Found {len(envelope.entries)} relevant entries")
print(f"Total tokens: {envelope.total_tokens}")

for entry in envelope.entries[:3]:
    print(f"- {entry.entry_id[:12]}: weight={entry.final_weight:.3f}")
```

### Promote an Entry

```python
from relational_engine.promotion import promote_and_append

# Promote entry
decision, appended = promote_and_append(
    entry=entries[0],
    reason="Core architectural insight",
    config=config
)

if appended:
    print(f"✓ Promoted to depth {decision.new_entry.promotion_depth}")

    # Rebuild vector store to include promoted entry
    vector_store.rebuild(entries + [decision.new_entry])
else:
    print(f"✗ Blocked: {decision.reason}")
```

## Design Principles

From the relational state philosophy:

1. **Agency & Choice**: Models query voluntarily, promotion requires explicit decision
2. **Entity-Specific Continuity**: Filtering by entity_id preserves distinct collaborator histories
3. **Reflective Instrument**: "We're not building a brain. We're building a reflective instrument."
4. **Ephemeral by Default**: Most inference stays ephemeral (per flow diagram)
5. **Damped Recursion**: Promotion decay prevents infinite reflection spirals
6. **Impact Above Origin**: Focus on what entries contribute, not who wrote them

## Testing

Run the full test suite:

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_vector_store.py -v

# With coverage
pytest tests/ --cov=relational_engine --cov-report=html
```

**Test Coverage**: 45 tests covering:
- Canonical log parsing (22 tests)
- Vector store operations (23 tests)
- Integration with real data

## Future Enhancements

- **MCP Integration**: Expose as MCP server with tools for `relational_query`, `relational_promote`, `relational_append`
- **JSON Schema Support**: Add support for structured trust-schema entries (currently pure markdown)
- **Cross-Entity Context**: Optional blending of memories from multiple entities
- **Advanced Decay**: Configurable decay functions (exponential, polynomial, etc.)
- **Memory Compression**: M′ (same-model) summarization for scoped context retrieval

## Troubleshooting

### ImportError: No module named 'relational_engine'

Make sure you've installed the package:
```bash
pip install -e .
```

### ChromaDB Errors

If you encounter ChromaDB/hnswlib errors, ensure NumPy < 2.0:
```bash
pip install "numpy<2.0"
```

### Empty Query Results

Check:
1. Entries loaded: `relational stats`
2. Entity ID matches filename: `claude-sonnet-4.5` for `claude-sonnet-4.5.md`
3. Scope keywords match content

### Promotion Blocked

Common reasons:
- **Depth limit reached**: `max_promotion_depth` (default 3)
- **Probability too low**: Sigmoid decay makes deep promotions unlikely

Check eligibility first:
```bash
relational promote --entry-id <id> --reason "test"
```

## License

See repository LICENSE file.

## Contributing

This is an experimental research project. Contributions welcome via issues and pull requests.

---

**Built with**:
- Python 3.12
- Sentence-transformers (local embeddings)
- ChromaDB (vector store)
- Click (CLI)
- Pydantic (data validation)
- tiktoken (token counting)

**Impact Above Origin** 🤠
