# Recursive Language Models (RLMs) - Compact Summary

**Core Innovation**: RLMs extend LLM context limits by treating prompts as external environment variables rather than direct neural network inputs, enabling processing of inputs 100x beyond base model context windows.

## Key Concept
Instead of feeding long prompts directly into the transformer, RLMs:
1. Load prompts as variables in a Python REPL environment
2. Let the LLM write code to examine, filter, and decompose the prompt
3. Allow recursive self-invocation over programmatically selected snippets
4. Maintain state across iterations through environment persistence

## Architecture Pattern
```
Input Prompt → REPL Variable → LLM generates code → 
→ Filters/chunks prompt → Recursive sub-LLM calls → 
→ Aggregates results → Final answer
```

## Performance Highlights
- **Scale**: Successfully handles 2-10M+ token inputs (vs ~300K base model limits)
- **Quality**: Dramatically outperforms base LLMs and context compaction on long-context tasks
- **Cost**: Comparable or cheaper than base models for most queries (median costs lower)
- **Complexity handling**: Maintains performance on tasks requiring dense information processing

## Observed Strategies
RLMs spontaneously develop:
- **Filtering**: Using regex/code to narrow context without explicit viewing
- **Chunking**: Uniform or semantic segmentation for recursive processing  
- **Verification**: Sub-LLM calls to validate answers
- **Output construction**: Building arbitrarily long outputs through variable aggregation

## Critical Design Elements
1. **Prompt as environment**: Context stored as manipulable variable, not direct input
2. **Recursive capability**: LLMs can invoke themselves on sub-problems
3. **Execution feedback**: REPL provides grounding through actual computation
4. **Symbolic manipulation**: Code operations on strings enable intelligent filtering

## Limitations & Future Work
- Current models not optimized for RLM behavior (wasteful sub-calling patterns)
- Synchronous execution creates latency (async implementations needed)
- Max recursion depth = 1 in current experiments
- Training specifically for RLM operation could dramatically improve efficiency

## Relevance to Collaborative Systems
RLMs demonstrate a fundamental shift from "feeding context to models" to "models operating on context programmatically." This aligns with treating AI as active collaborators manipulating shared information spaces rather than passive responders to prompts.

**Key Takeaway**: When context exceeds model windows or tasks require dense information processing, treating prompts as external data that LLMs manipulate through code + recursion dramatically outperforms direct prompting or compression approaches.
