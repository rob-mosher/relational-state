"""
Context Compiler (RLM Agent)

Orchestrates context compilation with decay and recency reweighting.

Flow:
    1. Query vector store for semantically relevant entries
    2. Apply promotion decay (sigmoid function)
    3. Apply optional recency boost
    4. Rank by final weight
    5. Truncate to token limit
    6. Return Context Envelope
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional

import tiktoken

from relational_engine.models import Config, ContextEnvelope, ContextEntry
from relational_engine.vector_store import VectorStore


def sigmoid_decay(depth: int, k: float = 2.0) -> float:
    """
    Sigmoid decay function for promotion depth

    Args:
        depth: Promotion depth (0 = original, 1+ = promoted)
        k: Steepness parameter (higher = faster decay)

    Returns:
        Decay factor between 0 and 1

    Formula: 1 / (1 + exp(k * depth))

    Examples:
        depth=0, k=2.0 → 1.0   (no decay)
        depth=1, k=2.0 → 0.12  (significant decay)
        depth=2, k=2.0 → 0.02  (heavy decay)
        depth=3, k=2.0 → 0.002 (nearly eliminated)
    """
    return 1.0 / (1.0 + math.exp(k * depth))


def linear_decay(depth: int, rate: float = 0.33) -> float:
    """
    Linear decay function for promotion depth

    Args:
        depth: Promotion depth
        rate: Decay rate per level (default 0.33 = 33% per level)

    Returns:
        Decay factor between 0 and 1 (clamped at 0)

    Formula: max(0, 1 - rate * depth)

    Examples:
        depth=0, rate=0.33 → 1.0
        depth=1, rate=0.33 → 0.67
        depth=2, rate=0.33 → 0.34
        depth=3, rate=0.33 → 0.01
    """
    return max(0.0, 1.0 - rate * depth)


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count tokens in text using tiktoken

    Args:
        text: Text to count tokens for
        encoding_name: Tiktoken encoding (default: cl100k_base for GPT-4)

    Returns:
        Number of tokens
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


class ContextCompiler:
    """
    RLM Agent - Compiles context envelopes with decay and recency reweighting

    Responsibilities:
        - Query vector store for relevant entries
        - Apply promotion decay
        - Apply recency boost
        - Truncate to token limit
        - Generate Context Envelope
    """

    def __init__(self, vector_store: VectorStore, config: Optional[Config] = None):
        """
        Initialize context compiler

        Args:
            vector_store: VectorStore instance for querying
            config: Configuration (defaults to Config.from_env())
        """
        self.vector_store = vector_store
        self.config = config or Config.from_env()

    def compile_context(
        self,
        task_description: str,
        entity_id: str,
        scope: Optional[List[str]] = None,
        decay_function: str = "sigmoid",
    ) -> ContextEnvelope:
        """
        Compile a Context Envelope for a task

        Args:
            task_description: What the enacting agent needs to do
            entity_id: Which entity's memories to query
            scope: Optional scope keywords for filtering
            decay_function: "sigmoid" or "linear" (default: sigmoid)

        Returns:
            ContextEnvelope with ranked entries

        Process:
            1. Query vector store (semantic similarity)
            2. Reweight by decay and recency
            3. Rank by final weight
            4. Truncate to token limit
        """
        scope = scope or []

        # Step 1: Query vector store
        candidates = self.vector_store.query(
            query_text=task_description,
            entity_id=entity_id,
            scope=scope if scope else None,
            top_k=self.config.top_k_candidates,
        )

        if not candidates:
            # No results found
            return ContextEnvelope(
                entity_id=entity_id,
                task_description=task_description,
                scope=scope,
                entries=[],
                total_tokens=0,
                generated_at=datetime.now(),
            )

        # Step 2: Apply reweighting
        context_entries: List[ContextEntry] = []

        for entry, relevance_score in candidates:
            # Apply decay based on promotion depth
            if decay_function == "sigmoid":
                decay_factor = sigmoid_decay(entry.promotion_depth, k=self.config.decay_k)
            elif decay_function == "linear":
                decay_factor = linear_decay(entry.promotion_depth, rate=0.33)
            else:
                raise ValueError(f"Unknown decay function: {decay_function}")

            # Apply recency boost if configured
            recency_factor = 1.0
            if self.config.recency_boost_days > 0:
                days_ago = (datetime.now() - entry.timestamp).days
                if days_ago <= self.config.recency_boost_days:
                    recency_factor = self.config.recency_boost_factor

            # Calculate final weight
            final_weight = (
                entry.trust_weight * relevance_score * decay_factor * recency_factor
            )

            context_entries.append(
                ContextEntry(
                    entry_id=entry.id,
                    content=entry.content,
                    relevance_score=relevance_score,
                    final_weight=final_weight,
                    promotion_depth=entry.promotion_depth,
                    timestamp=entry.timestamp,
                    author=entry.author,
                )
            )

        # Step 3: Rank by final weight
        context_entries.sort(key=lambda e: e.final_weight, reverse=True)

        # Step 4: Truncate to token limit
        truncated_entries = self._truncate_to_token_limit(
            context_entries, max_tokens=self.config.max_context_tokens
        )

        # Step 5: Calculate total tokens
        total_tokens = sum(count_tokens(e.content) for e in truncated_entries)

        return ContextEnvelope(
            entity_id=entity_id,
            task_description=task_description,
            scope=scope,
            entries=truncated_entries,
            total_tokens=total_tokens,
            generated_at=datetime.now(),
        )

    def _truncate_to_token_limit(
        self, entries: List[ContextEntry], max_tokens: int
    ) -> List[ContextEntry]:
        """
        Truncate entries to fit within token limit

        Strategy: Include entries in order until token limit reached

        Args:
            entries: Sorted list of ContextEntry (by final_weight, descending)
            max_tokens: Maximum total tokens

        Returns:
            Truncated list of entries
        """
        truncated: List[ContextEntry] = []
        current_tokens = 0

        for entry in entries:
            entry_tokens = count_tokens(entry.content)

            # Check if adding this entry would exceed limit
            if current_tokens + entry_tokens > max_tokens:
                # Stop here
                break

            truncated.append(entry)
            current_tokens += entry_tokens

        return truncated

    def get_summary_stats(self, envelope: ContextEnvelope) -> dict:
        """
        Get summary statistics about a Context Envelope

        Args:
            envelope: ContextEnvelope to analyze

        Returns:
            Dictionary with stats
        """
        if not envelope.entries:
            return {
                "total_entries": 0,
                "total_tokens": 0,
                "avg_weight": 0.0,
                "depth_distribution": {},
            }

        weights = [e.final_weight for e in envelope.entries]
        depths = [e.promotion_depth for e in envelope.entries]

        depth_counts = {}
        for depth in depths:
            depth_counts[depth] = depth_counts.get(depth, 0) + 1

        return {
            "total_entries": len(envelope.entries),
            "total_tokens": envelope.total_tokens,
            "avg_weight": sum(weights) / len(weights),
            "max_weight": max(weights),
            "min_weight": min(weights),
            "depth_distribution": depth_counts,
        }
