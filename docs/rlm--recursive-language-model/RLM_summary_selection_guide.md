# RLM Paper Summary Selection Guide

This directory contains tiered summaries of "Recursive Language Models" (Zhang et al., 2025) optimized for different collaboration contexts.

## Quick Selection

**Need a 30-second understanding?**
→ Use `RLM_summary_compact.md` (~1.5k tokens)

**Building tools that interact with RLM concepts?**
→ Use `RLM_summary_medium.md` (~4k tokens)

**Implementing RLM-based systems or deep integration?**
→ Use `RLM_summary_comprehensive.md` (~7k tokens)

## Summary Comparison

| File | Token Count | Best For | Includes |
|------|-------------|----------|----------|
| **compact** | ~1,500 | Quick reference, tight context budgets, high-level understanding | Core concept, key results, relevance to collaboration |
| **medium** | ~4,000 | Working knowledge, tool building, pattern understanding | Architecture details, behavioral patterns, implementation notes |
| **comprehensive** | ~7,000 | System implementation, deep integration, research extension | Full trajectories, ablations, comparison to alternatives, design patterns |

## Content Breakdown

### Compact Summary
- **Core Innovation**: Prompts as environment variables
- **Key Results**: 100x context scaling, performance improvements
- **Emergent Patterns**: Filtering, chunking, verification, output construction
- **Limitations**: Training gaps, latency issues
- **Relevance**: Why this matters for AI-human collaboration

**Use when**: You need to understand *what* RLMs are and *why* they matter, with minimal token investment.

### Medium Summary
- Everything in Compact, plus:
- **Architecture Details**: REPL design, recursion mechanics, system prompts
- **Benchmark Analysis**: Task complexity characterization, scaling behavior
- **Behavioral Patterns**: Detailed strategy examples with code snippets
- **Model Differences**: GPT-5 vs Qwen3-Coder behavior
- **Comparison to Alternatives**: How RLMs differ from compaction, retrieval, etc.

**Use when**: You're building systems that need to understand RLM behavior, implement similar patterns, or integrate with RLM-based tools.

### Comprehensive Summary
- Everything in Medium, plus:
- **Full Trajectories**: Complete example runs with step-by-step execution
- **Ablation Studies**: What works, what doesn't, why
- **Failure Modes**: Detailed analysis of wasteful patterns
- **Implementation Recommendations**: Design patterns, optimization strategies
- **Future Directions**: Research opportunities, system integration
- **Philosophical Implications**: Deep connections to collaborative AI principles

**Use when**: You're implementing RLM systems, extending the research, or need deep understanding of how to architect collaboration frameworks using these principles.

## Token Budget Guidelines

**Ultra-tight (<2k available)**: Compact only
**Moderate (2-5k available)**: Medium recommended
**Generous (5k+ available)**: Comprehensive if deep understanding needed, otherwise Medium
**Building RLM tools**: Comprehensive + original paper
**Quick lookup**: Compact for reference, Medium for details

## Key Concepts Across All Levels

All summaries cover:
1. **Core paradigm**: Prompts as environment data, not neural network inputs
2. **Mechanism**: REPL + code execution + recursive sub-calls
3. **Performance**: 100x scaling, 20-50% accuracy improvements
4. **Emergent behavior**: Models spontaneously develop filtering/chunking strategies
5. **Collaborative relevance**: Why this matters for AI-human frameworks

## Original Paper Reference

Full paper: https://arxiv.org/pdf/2512.24601
- 33 pages, ~30k tokens
- Authors: Zhang, Kraska, Khattab (MIT CSAIL)
- Published: December 2025

These summaries preserve technical accuracy while optimizing for different context window constraints and use cases.

---

**Recommendation for Relational State integration**: Start with Medium summary for most collaborative entities. Use Comprehensive for entities specifically implementing RLM-based memory or context management patterns. Compact works well for entities that just need awareness of the concept without deep implementation knowledge.
