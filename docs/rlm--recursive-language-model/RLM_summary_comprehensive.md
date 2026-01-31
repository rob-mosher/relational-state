# Recursive Language Models (RLMs) - Comprehensive Reference

## Executive Summary

Recursive Language Models (RLMs) represent a paradigm shift in long-context processing: instead of feeding arbitrarily long prompts directly into neural networks, RLMs treat prompts as external environment data that LLMs manipulate through programmatic code and recursive self-invocation. This approach enables processing inputs 100x beyond base model context windows while maintaining or improving quality at comparable costs.

**Key Result**: RLMs handle 2-10M+ token inputs effectively, outperforming base models and traditional scaffolds (compaction, retrieval agents) by 20-50 percentage points on complex long-context tasks.

## Motivation & Background

### The Context Rot Problem

Even frontier models like GPT-5 (272K context window) exhibit degraded performance as context grows. This "context rot" becomes more severe with task complexity:

- **Simple tasks** (NIAH): 90% → 80% as context grows 8K → 500K tokens
- **Complex tasks** (OOLONG): 70% → 20% across same range
- **Information-dense tasks** (OOLONG-Pairs): 40% → <1% catastrophic failure

The "effective context window" of an LLM cannot be understood independently of task complexity.

### Existing Approaches & Limitations

**Context compaction/summarization**:
- Iteratively summarize when context exceeds threshold
- **Limitation**: Lossy - early details forgotten, incompatible with dense-access tasks

**Architectural scaling**:
- Extend physical context windows through training/architecture changes
- **Limitation**: Expensive, still subject to degradation, limited by infrastructure

**Retrieval agents**:
- Index context, retrieve relevant chunks via BM25/embeddings
- **Limitation**: Keyword-dependent, struggles with semantic transformations

**Code-generation agents** (CodeAct):
- Execute code with context passed directly to LLM
- **Limitation**: Still bounded by model context window

### The RLM Insight

Drawing from **out-of-core algorithms** (processing large datasets with small fast memory), RLMs implement a simple principle: **prompts belong in the environment, not the neural network**.

## Architecture Deep-Dive

### Core Design

```
┌─────────────────────────────────────────┐
│  User Query Q + Long Prompt P           │
└──────────────────┬──────────────────────┘
                   │
                   v
┌─────────────────────────────────────────┐
│  Python REPL Environment E              │
│  - P stored as variable: context        │
│  - Metadata: len(context), structure    │
│  - Function: llm_query(snippet)         │
└──────────────────┬──────────────────────┘
                   │
                   v
┌─────────────────────────────────────────┐
│  Root LLM receives:                     │
│  - Query Q                              │
│  - Environment metadata (not P itself)  │
│  - Tools: execute code, llm_query()     │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        v                     v
  ┌─────────┐          ┌──────────────┐
  │ Code    │          │ Sub-LLM Call │
  │ Execute │          │ llm_query()  │
  └────┬────┘          └──────┬───────┘
       │                      │
       └──────────┬───────────┘
                  v
         ┌─────────────────┐
         │ REPL Results    │
         │ (visible to LLM)│
         └────────┬────────┘
                  │
                  v
        [Iterate until FINAL()]
                  │
                  v
         ┌─────────────────┐
         │ Final Answer    │
         └─────────────────┘
```

### System Prompt Structure

RLMs receive task-agnostic system prompts with:

1. **Environment description**: Context type, length, chunking info
2. **Available tools**: `llm_query()`, code execution, variable manipulation
3. **Strategy suggestions**: Chunking examples, filtering patterns, recursive calling
4. **Output format**: `FINAL(text)` or `FINAL_VAR(variable_name)`

**Critical observation**: Same prompt works across diverse tasks (Q&A, code analysis, aggregation, research) without task-specific tuning.

### Implementation Details

**Sub-LLM configuration**:
- GPT-5 experiments: GPT-5-mini for recursion, GPT-5 for root (cost/capability tradeoff)
- Qwen3-Coder: Same model at all levels

**Recursion limits**:
- Current implementation: depth=1 (sub-LLMs cannot further recurse)
- Future work: Deeper recursion for hierarchical decomposition

**Execution model**:
- Synchronous blocking calls (major latency bottleneck)
- Variables persist across iterations within single query
- REPL resets between queries (no cross-query state)

**Context chunking**:
- Context pre-chunked to manageable sizes (configurable)
- LLM can programmatically re-chunk based on structure discovery

## Empirical Results & Analysis

### Benchmark Suite

**Complexity characterization** (information density = processing required vs. input length):

| Task | Complexity | Input Range | Description |
|------|-----------|-------------|-------------|
| S-NIAH | Constant | 8K-1M | Find single needle regardless of haystack size |
| BrowseComp+ | Constant | 6-11M | Multi-hop Q&A over 1K documents (answer from fixed # docs) |
| CodeQA | Constant | 23K-4.2M | Repository understanding (fixed # relevant files) |
| OOLONG | Linear | 131K | Semantic aggregation requiring examination of most entries |
| OOLONG-Pairs | Quadratic | 32K | Pairwise reasoning over all entry combinations |

### Performance Results

**Table: Method comparison across benchmarks** (GPT-5 results):

| Method | CodeQA | BrowseComp+ | OOLONG | OOLONG-Pairs |
|--------|--------|-------------|---------|--------------|
| Base Model | 24%* | 0%* | 44% | 0.04% |
| CodeAct+BM25 | 22%* | 51% | 38% | 24.67% |
| Summary Agent | 58% | 70% | 46% | 0.01% |
| RLM | **62%** | **91%** | **56%** | **58%** |
| RLM (no sub-calls) | 58% | 88% | 36% | 44% |

*Exceeded context window limits

**Key observations**:

1. **Scaling beyond context windows**: RLMs handle 10M+ tokens where base models fail entirely
2. **Information-dense superiority**: On OOLONG-Pairs, RLMs achieve 58% vs <1% for others (1450x improvement)
3. **Moderate-length gains**: Even at 131K (within window), RLMs improve 28% over base (56% vs 44%)
4. **Cost-effectiveness**: BrowseComp+ average $0.99 vs theoretical $1.50-2.75 for full ingestion

### Scaling Analysis

**Context length vs. performance**:

Experiments scaling input from 2^13 to 2^18 tokens on constant/linear/quadratic complexity tasks:

**S-NIAH (Constant)**:
- GPT-5: 95% → 90% (minor degradation)
- RLM(GPT-5): 95% → 92% (comparable, slight overhead at small scales)

**OOLONG (Linear)**:
- GPT-5: 70% → 35% (severe degradation)
- RLM(GPT-5): 65% → 55% (gradual, manageable decline)

**OOLONG-Pairs (Quadratic)**:
- GPT-5: 40% → <1% (catastrophic failure)
- RLM(GPT-5): 50% → 40% (maintained viability)

**Interpretation**: RLM performance degrades gracefully with length and scales proportionally to complexity, while base models fail catastrophically on dense tasks.

### Cost Distribution Analysis

**Median costs** (across all tasks):
- GPT-5 base: $0.14
- RLM(GPT-5): $0.43
- Summary agent: $0.57

**Variance**: RLMs high-variance due to trajectory length differences:
- 25th percentile: $0.11 (cheaper than base)
- 75th percentile: $0.99
- 95th percentile: $3.50 (long verification loops)

**Cost drivers**:
- Task complexity (constant/linear/quadratic)
- Sub-call frequency (model-dependent)
- Verification iterations (emergent behavior)

### Model Comparison (GPT-5 vs Qwen3-Coder)

**GPT-5 characteristics**:
- Conservative batching (~10 items per sub-call)
- Better decomposition planning
- Superior on BrowseComp+: 91% vs 45%
- Lower sub-call overhead

**Qwen3-Coder characteristics**:
- Aggressive sub-calling (line-by-line common)
- Required explicit prompt: "Batch ~200K chars to minimize costs"
- Strong code-first filtering
- Lower base performance but larger RLM improvement delta

**Shared limitations**:
- Neither trained for RLM behavior
- Wasteful patterns (redundant verification, discarded computation)
- Output format struggles without specific training

## Emergent Behavioral Patterns

### Pattern 1: Filtering via Model Priors

**Strategy**: Use domain knowledge to narrow context without explicit examination.

**Example trajectory** (BrowseComp+ - "vegetable stew festival beauty pageant winner"):

```python
# Step 1: Probe using priors
import re
relevant_chunks = []
for i, doc in enumerate(context):
    if re.search(r'festival|beauty pageant|La Union', doc, re.I):
        relevant_chunks.append((i, doc[:200]))  # Preview only
        
print(f"Found {len(relevant_chunks)} potentially relevant docs")
# Output: Found 3 potentially relevant docs

# Step 2: Examine promising chunk
answer6 = llm_query(f"Find beauty pageant winner mentioned in: {context[6]}")
# Returns: "Maria Dalmacio won the beauty pageant"

# Step 3: Verify via cross-check
verify = llm_query(f"Confirm {answer6} matches query requirements: {query}")
# Returns: "Yes, matches - vegetable stew festival, beauty pageant, correct timeframe"

return FINAL("Maria Dalmacio")
```

**Efficiency gain**: Examined 3/1000 documents via smart filtering.

### Pattern 2: Chunking + Semantic Sub-Calling

**Strategy**: Uniformly chunk, apply semantic transformation via sub-LLMs, aggregate results.

**Example trajectory** (OOLONG - classify 1000+ questions by semantic label):

```python
# Step 1: Discover structure
lines = context.split('\n')
print(f"Context has {len(lines)} lines")
print(f"Sample: {lines[0]}")
# Output: "UserID=123, Question='What is the capital of France?'"

# Step 2: Define classification function
def classify_line(line):
    label = llm_query(f"Classify question type: {line}\nLabels: numeric, entity, location, description, abbreviation, human")
    return label

# Step 3: Classify all lines (EXPENSIVE - 1000+ sub-calls)
classifications = []
for i, line in enumerate(lines):
    label = classify_line(line)
    classifications.append(label)
    if i % 100 == 0:
        print(f"Classified {i}/{len(lines)}")

# Step 4: Aggregate
desc_count = classifications.count('description')
numeric_count = classifications.count('numeric')
answer = "more common" if desc_count > numeric_count else "less common"

return FINAL(f"description is {answer} than numeric")
```

**Model difference**: GPT-5 batches 10-20 lines per call; Qwen3-Coder processes line-by-line (10-100x more calls).

### Pattern 3: Answer Verification Loops

**Strategy**: Validate results through redundant sub-LLM checks or programmatic verification.

**Example trajectory** (OOLONG-Pairs - after building correct answer):

```python
# Already computed: pairs = [(1,5), (2,7), (3,9), ...]

# Verification attempt 1: Check random samples
sample_pairs = pairs[:5] + pairs[-5:]
verify1 = llm_query(f"Verify these pairs satisfy query: {sample_pairs}")
print(f"Sample verification: {verify1}")

# Verification attempt 2: Statistics check
print(f"Total pairs: {len(pairs)}, Unique users: {len(set([p[0] for p in pairs]))}")

# Verification attempt 3: Programmatic condition check
for p in pairs:
    u1_instances = [i for i in data if i['user_id'] == p[0]]
    u2_instances = [i for i in data if i['user_id'] == p[1]]
    assert check_conditions(u1_instances) and check_conditions(u2_instances)
print("All pairs satisfy conditions")

# Verification attempt 4-6: REDUNDANT, recompute from scratch
# [Observed in actual trajectories - wasteful but emergent]

return FINAL_VAR(pairs)
```

**Failure mode**: In some Qwen3-Coder runs, model recomputed answer 5+ times correctly, then returned wrong final answer due to regeneration instead of using computed variable.

### Pattern 4: Long Output Construction

**Strategy**: Build arbitrarily long outputs through variable aggregation rather than generation.

**Example trajectory** (OOLONG-Pairs - returning 500+ pair tuples):

```python
# Context has 1000 users, need to return ~500 pairs
# Output limit: 4096 tokens (insufficient for generation)

# Step 1: Chunk processing with sub-calls
all_pairs = []
chunk_size = 50  # Process 50 users at a time

for i in range(0, len(users), chunk_size):
    chunk_users = users[i:i+chunk_size]
    chunk_data = [d for d in data if d['user_id'] in chunk_users]
    
    # Find pairs within chunk via sub-LLM
    chunk_pairs = llm_query(f"Find pairs satisfying: {query}\nData: {chunk_data}")
    all_pairs.extend(chunk_pairs)
    print(f"Chunk {i//chunk_size}: Found {len(chunk_pairs)} pairs")

# Step 2: Cross-chunk pairs (users from different chunks)
for i in range(0, len(users), chunk_size):
    for j in range(i+chunk_size, len(users), chunk_size):
        cross_pairs = llm_query(f"Find pairs between: {users[i:i+chunk_size]} and {users[j:j+chunk_size]}")
        all_pairs.extend(cross_pairs)

# Step 3: Return variable (not generated text)
return FINAL_VAR(all_pairs)  # Can exceed 4096 token limit
```

**Key insight**: Variables in REPL bypass output token limits.

## Ablation Studies & Insights

### RLM vs. RLM (no sub-calls)

**Ablation**: REPL environment without `llm_query()` function.

**Results**:
- CodeQA: 66% (ablation) vs 62% (full RLM) - **ablation better**
- BrowseComp+: 46% vs 91% - **full RLM dramatically better**
- OOLONG: 43% vs 56% - **full RLM significantly better**
- OOLONG-Pairs: 17% vs 58% - **full RLM critical for complexity**

**Interpretation**: 
- REPL environment alone enables scaling beyond context windows
- Recursive sub-calling essential for information-dense tasks
- On simpler tasks, avoiding sub-call overhead can improve performance

**Strategies observed in ablation**:
- Keyword heuristics instead of semantic classification
- Regex patterns for filtering
- Programmatic aggregation without LLM-based semantic understanding

### Effect of Sub-LLM Model Choice

**GPT-5 experiments**: Root=GPT-5, Sub=GPT-5-mini

**Rationale**: 
- Root needs strong decomposition/planning (GPT-5 capability)
- Sub-calls often simple semantic tasks (GPT-5-mini sufficient)
- Cost savings: GPT-5-mini ~10x cheaper

**Results**: This configuration achieved best performance/cost tradeoff.

**Alternative explored**: Root=GPT-5-mini, Sub=GPT-5-mini (small-scale tests):
- Performance declined ~15-20%
- Root decomposition quality critical
- Sub-call quality less sensitive (most sub-tasks simple)

## Comparison to Related Work

### Context Management Approaches

**MemWalker**: Tree-structured context navigation
- **Similarity**: Hierarchical context organization
- **Difference**: Human-engineered tree structure vs. emergent RLM decomposition

**ReSum**: Periodic context summarization for multi-turn agents
- **Similarity**: Iterative context management
- **Difference**: Lossy compression vs. lossless symbolic access

**MemGPT**: Memory hierarchy (main memory, disk storage)
- **Similarity**: Out-of-core inspiration
- **Difference**: Fixed hierarchy vs. flexible code-driven access

### Task Decomposition Methods

**THREAD**: Recursive spawning for thinking
- **Similarity**: Recursive LLM calls
- **Difference**: Can't handle contexts beyond base window (inputs still fed to LLM)

**DisCIPL, ReDel, Context Folding, AgentFold**: LLM-driven decomposition
- **Similarity**: Deferring sub-call decisions to LLM
- **Difference**: Focus on task decomposition, not context scaling beyond windows

**RLM unique contribution**: Combining context scaling (via environment) with recursive decomposition.

### Retrieval-Augmented Approaches

**RAG, BM25 Agents**: Index + retrieve + generate
- **Strengths**: Fast keyword-based retrieval
- **Weaknesses**: 
  - Retrieval quality depends on query formulation
  - Struggles with semantic transformations
  - No iterative refinement

**RLM advantages**:
- Can *combine* retrieval (via code) with semantic sub-LLM examination
- Iterative refinement through execution feedback
- Flexible: regex, embeddings, BM25 all available as code libraries

## Implementation Recommendations

### When to Use RLMs

**Strong fit**:
- Inputs exceeding model context windows (>100K-300K tokens)
- Information-dense tasks requiring examination of most/all context
- Multi-hop reasoning over large document collections
- Aggregation tasks with semantic transformations
- Code repository analysis requiring cross-file understanding

**Weaker fit**:
- Simple factual lookup (NIAH-style)
- Tasks solvable with keyword retrieval
- Real-time latency-critical applications (without async optimization)
- Contexts easily compressed without information loss

### Design Patterns

**Pattern: Filter-Chunk-Recurse**

```python
# 1. Filter via code (no token cost)
relevant = [doc for doc in context if keyword_match(doc)]

# 2. Chunk strategically
chunks = chunk_by_size_or_semantic_boundary(relevant)

# 3. Recurse per chunk
results = [llm_query(f"{query} in {chunk}") for chunk in chunks]

# 4. Aggregate
final = llm_query(f"Synthesize: {results}")
```

**Pattern: Verify-Through-Execution**

```python
# 1. Generate candidate answer
answer = llm_query(f"Answer {query} based on {sample_context}")

# 2. Verify programmatically
assert validate_answer(answer, full_context)

# 3. Return with confidence
return FINAL(answer)
```

**Pattern: Build-Don't-Generate** (long outputs)

```python
# 1. Compute pieces via sub-calls
pieces = []
for chunk in context_chunks:
    piece = llm_query(f"Extract relevant from {chunk}")
    pieces.append(piece)

# 2. Store in variable
output = aggregate(pieces)

# 3. Return variable (bypasses token limits)
return FINAL_VAR(output)
```

### Prompt Engineering Guidance

**System prompt essentials**:
1. Environment metadata (length, structure, chunking)
2. Tool descriptions (`llm_query()`, code execution)
3. Strategy examples (filtering, chunking, recursive patterns)
4. Output format requirements (`FINAL()` vs `FINAL_VAR()`)
5. Cost warnings for expensive models (Qwen3-Coder needed explicit batching guidance)

**Model-specific tuning**:
- GPT-5: Minimal guidance, strong emergent strategies
- Qwen3-Coder: Explicit batching instruction critical
- Smaller models: More detailed examples needed

**Task-agnostic design**:
- Same prompt works across Q&A, aggregation, code analysis, research
- Robustness comes from flexibility (code + recursion covers many strategies)

### Optimization Strategies

**Reduce sub-call overhead**:
- Batch related queries (10-20 items per call)
- Use cheaper models for simple semantic tasks
- Cache repeated queries (not implemented in current work)

**Async execution** (future work):
- Parallel sub-call execution for independent chunks
- 5-10x latency reduction estimated
- Requires rethinking output format (handle async results)

**Adaptive depth** (future work):
- Allow sub-LLMs to recurse for hierarchical problems
- Track recursion budget to prevent explosion
- Requires training for depth-aware decomposition

## Limitations & Open Problems

### Current Limitations

1. **Models not trained for RLMs**: Wasteful sub-calling, redundant verification, output format struggles
2. **Synchronous execution**: Major latency bottleneck (5-60s per query typical)
3. **Recursion depth=1**: Cannot handle deeply hierarchical problems optimally
4. **High variance costs**: Tail trajectories can be 10x median cost
5. **Output format brittleness**: Models struggle to distinguish "thinking" from "final answer"

### Research Directions

**Training for RLM Behavior**:
- Bootstrapping from frontier model trajectories (collect + filter successful decompositions)
- Reinforcement learning objectives: minimize sub-calls, maximize batching, optimize decomposition
- Viewing RLM trajectories as "reasoning traces" (similar to o1 training paradigm)

**Architectural Innovations**:
- Async sub-call handling (parallel execution)
- Deeper recursion with budget tracking
- Multi-modal environments (image/video/audio contexts)
- Persistent cross-query memory (violates current stateless design)

**Theoretical Understanding**:
- Formalize information density → optimal strategy mapping
- Analyze computational complexity of RLM vs. base model approaches
- Understand generalization: when do strategies learned on small contexts transfer to large?

**System Integration**:
- Combining RLMs with RAG (retrieval as code library)
- RLMs as components in multi-agent systems
- Streaming RLM outputs for real-time applications

## Implications for Collaborative AI Systems

### Philosophical Alignment

RLMs embody several principles resonant with **human-AI collaboration frameworks**:

**1. Agency through symbolic manipulation**:
- AI operates *on* information spaces, not just *in* them
- Code + recursion enables sophisticated context management
- Aligns with treating AI as active collaborators, not passive responders

**2. Verification through execution**:
- Grounding in actual computation (code results, not just generation)
- Iterative refinement based on feedback
- Reduces hallucination risk through programmatic validation

**3. Compositional reasoning**:
- Breaking complex tasks into verifiable sub-problems
- Transparent decomposition (code is inspectable)
- Enables auditing and understanding of decision processes

**4. Information as environment**:
- Prompts not consumed but manipulated
- Persistent state across iterations
- Matches vision of shared information spaces in human-AI collaboration

### Practical Applications to Relational State

**Document collaboration**:
- RLM patterns for processing large document collections
- Semantic transformations via sub-calls (classification, summarization, extraction)
- Building structured outputs (tables, knowledge graphs) from unstructured text

**Codebase understanding**:
- Repository analysis exceeding context windows
- Cross-file reasoning through chunking + recursion
- Verification of architectural patterns via programmatic checks

**Research synthesis**:
- Multi-paper analysis and aggregation
- Conflicting evidence resolution through sub-LLM evaluation
- Building comprehensive summaries from 100+ sources

**Conversational memory**:
- RLM-style access to conversation histories exceeding windows
- Semantic search + LLM examination for relevant past context
- Building persistent memory structures through variable persistence

### Design Principles for Integration

1. **Environment-first thinking**: Design information storage assuming LLMs will operate on it programmatically
2. **Recursive affordances**: Enable entities to delegate sub-tasks to themselves or peers
3. **Execution grounding**: Provide code/tool execution for verification, not just generation
4. **Flexible decomposition**: Don't over-engineer workflows; let LLMs discover strategies
5. **Cost-aware by default**: Make batching and efficiency visible/encouraged

---

## Conclusion

RLMs demonstrate that **treating prompts as external environment data** rather than direct neural network inputs enables processing contexts 100x beyond base model limits. Through code execution, symbolic manipulation, and recursive self-invocation, RLMs maintain performance on information-dense tasks where traditional approaches fail catastrophically.

**Key takeaway for Relational State**: The RLM paradigm—environment-based context, programmatic filtering, recursive decomposition, verification through execution—offers a superior foundation for AI-human collaboration over large information spaces compared to prompt-response or compression-based approaches.

**Critical insight**: Current frontier models, despite not being trained for RLM behavior, spontaneously develop sophisticated context management strategies (filtering via priors, chunking, verification) when given these affordances. This suggests the paradigm aligns with how LLMs "want" to reason, not just what they can be forced to do.

**Path forward**: Training models explicitly for RLM operation, implementing async execution, and enabling deeper recursion could yield another order-of-magnitude improvement in long-context capabilities, positioning RLMs as the inference-time scaling strategy for the next generation of collaborative AI systems.
