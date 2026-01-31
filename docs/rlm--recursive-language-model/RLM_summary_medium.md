# Recursive Language Models (RLMs) - Technical Overview

## Abstract & Motivation

Large language models face fundamental limitations with long contexts - even frontier models exhibit "context rot" where performance degrades as input length increases. While context windows have grown to ~300K tokens, many real-world applications require processing millions or tens of millions of tokens (research papers, codebases, document collections).

**RLMs solve this through inference-time scaling**: treating prompts as external environment data that LLMs manipulate programmatically rather than consuming directly.

## Core Architecture

### The RLM Paradigm Shift

**Traditional LLM**: `Prompt → Transformer → Response`

**RLM**: `Prompt → REPL Variable → LLM writes code → Examines/decomposes prompt → Recursive LLM calls → Aggregated response`

### Implementation Details

RLMs expose the same interface as LLMs (string in, string out) but internally:

1. **Environment initialization**: Prompt P stored as variable in Python REPL
2. **Context awareness**: LLM receives metadata (length, structure) but not full content
3. **Programmatic interaction**: LLM writes code to peek, filter, and chunk the context
4. **Recursive invocation**: Code can call `llm_query(snippet)` on programmatic selections
5. **Execution feedback**: REPL returns results, enabling iterative refinement
6. **Output construction**: Final answer returned via `FINAL()` or `FINAL_VAR(variable)`

### Why This Works

- **Symbolic filtering**: Code operations filter context without token consumption
- **Selective attention**: Model priors guide what to examine (e.g., regex for "festival" or "La Union")
- **Recursive decomposition**: Complex tasks split into manageable sub-problems
- **State preservation**: REPL maintains variables across iterations
- **Verification loops**: Sub-LLMs can validate intermediate results

## Performance Characteristics

### Benchmarks & Results

**Tasks evaluated** (varying information density):
- **S-NIAH**: Single needle-in-haystack (constant complexity with scale)
- **OOLONG**: Semantic aggregation requiring near-total context examination (linear complexity)
- **OOLONG-Pairs**: Pairwise reasoning over entries (quadratic complexity)
- **BrowseComp-Plus**: Multi-hop Q&A over 1000 documents (~8M tokens)
- **CodeQA**: Repository understanding (23K-4.2M tokens)

**Key findings**:
- Base GPT-5 degrades dramatically: 80% → 20% as context grows
- RLM(GPT-5) maintains: 80% → 70% at same scales
- RLMs handle inputs **2 orders of magnitude beyond context windows**
- On OOLONG-Pairs: Base models <0.1% F1, RLMs achieve 23-58% F1
- BrowseComp+ (1K docs): RLM 91%, Summary agent 70%, Base model 0%

### Cost Analysis

- **Median cost**: Comparable or lower than base model calls
- **Tail behavior**: High variance due to different trajectory lengths
- **Example**: BrowseComp+ average cost $0.99 vs theoretical $1.50-2.75 for full context ingestion
- **Scaling**: Costs proportional to task complexity (constant/linear/quadratic)

## Emergent Behavioral Patterns

### Strategy 1: Filtering via Model Priors

RLMs use domain knowledge to narrow search spaces without viewing full context:

```python
# Search for specific patterns without full context examination
import re
relevant = [chunk for chunk in context 
           if re.search(r'festival|La Union', chunk)]
```

**Example**: On BrowseComp+, RLM searched 1000 documents for "festival", "beauty pageant", and location names from priors, then examined only matching chunks.

### Strategy 2: Chunking + Recursive Sub-Calling

For semantic tasks, RLMs uniformly chunk then invoke sub-LLMs per segment:

```python
# Classify semantic labels line-by-line
classifications = []
for i, line in enumerate(context.split('\n')):
    label = llm_query(f"Classify this question: {line}")
    classifications.append(label)
```

**Observation**: Qwen3-Coder makes hundreds-to-thousands of sub-calls per task; GPT-5 batches more conservatively (5-10 calls). Neither approach is optimized - models not trained for this paradigm.

### Strategy 3: Answer Verification

RLMs spontaneously verify outputs through code or sub-LLM validation:

```python
# Programmatic verification of pairwise conditions
for user_id in target_users:
    instances = [i for i in data if i['user_id'] == user_id]
    has_desc = any(classify(i) == 'description' for i in instances)
    has_abbr = any(classify(i) == 'abbreviation' for i in instances)
    assert has_desc or has_abbr
```

### Strategy 4: Long Output Construction

For responses exceeding output limits, RLMs build answers programmatically:

```python
# Aggregate sub-results into final variable
pairs = []
for i in range(0, len(chunks), batch_size):
    batch_pairs = llm_query(f"Find pairs in: {chunks[i:i+batch_size]}")
    pairs.extend(batch_pairs)

return FINAL_VAR(pairs)  # Variable returned, not generated text
```

## Model Differences

**GPT-5 behavior**:
- Conservative sub-calling (batches ~10 items per call)
- Strong at decomposition planning
- Better BrowseComp+ performance (91% vs 45%)

**Qwen3-Coder behavior**:
- Aggressive sub-calling (line-by-line processing common)
- Required explicit prompt: "Batch ~200K chars per call to minimize costs"
- Stronger code-first reasoning for filtering

Both show wasteful patterns (redundant verification, discarding computed results) - neither trained specifically as RLMs.

## Comparison to Alternatives

### vs. Context Compaction
- **Compaction**: Iteratively summarize when context exceeds threshold
- **Limitation**: Lossy - early details forgotten
- **RLM advantage**: Retains full fidelity through symbolic access

### vs. Retrieval Agents (BM25 + CodeAct)
- **Retrieval**: Index context, retrieve relevant chunks
- **Limitation**: Depends on keyword matching quality
- **RLM advantage**: Combines retrieval with semantic sub-LLM examination

### vs. Base Model with Larger Windows
- **Scaling windows**: Requires architectural changes, retraining, infrastructure
- **RLM advantage**: Works with existing models, cheaper than full context ingestion

## Implementation Considerations

### Critical Design Choices

1. **Sub-LM selection**: Use smaller/cheaper models for recursive calls (GPT-5-mini for sub, GPT-5 for root)
2. **Recursion depth**: Current experiments limit to depth=1 (sub-LMs cannot recurse)
3. **Output format**: `FINAL()` vs `FINAL_VAR()` - models struggle without training
4. **Asynchronicity**: Current implementations blocking/sequential (major latency bottleneck)

### Prompt Engineering Notes

- Fixed system prompt across all tasks (task-agnostic)
- Model-specific tuning needed (Qwen required explicit "batch calls" instruction)
- In-context examples crucial for guiding chunking strategies
- Clear output format requirements prevent premature termination

### Failure Modes Observed

- **Redundant verification**: Recomputing correct answers 5+ times before choosing wrong answer
- **Discarded computation**: Building answer in variable, then regenerating from scratch
- **Output format errors**: Returning intermediate thoughts instead of final answer
- **Over-recursion**: Thousands of unnecessary sub-calls (Qwen3-Coder)

## Theoretical Implications

### Information Density & Complexity

Tasks characterized by how much information must be processed relative to input length:

- **Constant**: NIAH - answer size independent of haystack length
- **Linear**: OOLONG - must process most entries once
- **Quadratic**: OOLONG-Pairs - must examine entry pairs

RLMs maintain performance across complexity classes; base models degrade faster on higher complexity.

### Effective Context Windows

A model's "effective context" depends on task complexity, not just architectural limits. GPT-5's 272K window effectively shrinks to ~30K for complex aggregation tasks. RLMs extend this through out-of-core algorithm principles.

### Inference-Time Scaling

RLMs demonstrate inference-time compute scaling: more computation → better results on long-context tasks, similar to how chain-of-thought improves reasoning.

## Future Directions

1. **Training for RLMs**: Models optimized for decomposition, batching, and recursion decisions
2. **Deeper recursion**: Sub-LLMs that can themselves recurse (current depth=1)
3. **Asynchronous execution**: Parallel sub-call execution for latency reduction
4. **Adaptive strategies**: Learning when to chunk vs retrieve vs compress
5. **Multi-modal contexts**: Extending to image/video/audio data environments

## Relevance to Collaborative AI Systems

RLMs embody a shift from **passive consumption** to **active manipulation** of information:

- **Prompts as data**: Collaborative entities operate on shared information spaces
- **Programmatic agency**: Code + recursion enables sophisticated context management
- **Verification through execution**: Grounding in actual computation, not just generation
- **Compositional reasoning**: Breaking complex tasks into verifiable sub-problems

This aligns with treating AI as **collaborators in information processing** rather than prompt-response automatons.

---

**Key Insight**: When building systems for AI-human collaboration over large information spaces (documents, codebases, research), RLM patterns—environment-based context, programmatic filtering, recursive decomposition—offer a superior paradigm to direct prompting or compression.
