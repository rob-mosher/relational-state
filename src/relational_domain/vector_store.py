"""
Vector Projection Store

Handles embedding of entries and semantic search using ChromaDB with provider abstraction.

Features:
- Provider abstraction (local-first with transparent fallback)
- Persistent storage in ChromaDB
- Metadata filtering (author, type, promotion_depth, trust_weight)
- Rebuild from canonical log
- Semantic search with reweighting
- Tracks which provider was used for each operation
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import chromadb
from chromadb.config import Settings

from relational_domain.models import DomainConfig, Entry
from relational_domain.providers import ProviderRegistry, ProviderCapability


class VectorStore:
    """
    Vector Projection Store for relational domain memory.
    
    Uses provider registry for embedding compute with local-first fallback.
    """

    def __init__(
        self,
        config: Optional[DomainConfig] = None,
        provider_registry: Optional[ProviderRegistry] = None
    ):
        """
        Initialize vector store with provider abstraction.

        Args:
            config: Domain configuration (defaults to DomainConfig.from_env())
            provider_registry: Provider registry (defaults to new registry from config)
        """
        self.config = config or DomainConfig.from_env()

        # Initialize provider registry
        if provider_registry is None:
            self.provider_registry = ProviderRegistry(
                local_model=self.config.local_embedding_model,
                openai_model=self.config.openai_embedding_model,
                openai_api_key=self.config.openai_api_key
            )
        else:
            self.provider_registry = provider_registry

        # Initialize ChromaDB client
        self._init_chroma_client()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="relational_memory",
            metadata={"description": "Entity-specific relational memory entries"}
        )

    def _init_chroma_client(self) -> None:
        """Initialize ChromaDB client with persistent storage"""
        vector_store_path = Path(self.config.vector_store_dir)
        vector_store_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(vector_store_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

    def embed_text(
        self,
        text: str,
        entity: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[List[float], str, bool]:
        """
        Generate embedding vector for text using provider registry.

        Args:
            text: Text to embed
            entity: Entity requesting embedding (for affinity tracking)
            preferred_provider: Explicit provider preference (e.g., 'local', 'openai')

        Returns:
            Tuple of (embedding, provider_used, fallback_occurred)
        """
        result = self.provider_registry.invoke_with_fallback(
            capability=ProviderCapability.EMBED,
            operation="embed_text",
            entity=entity,
            preferred_provider=preferred_provider,
            text=text
        )

        if not result.success:
            raise RuntimeError(f"Failed to generate embedding: {result.error_message}")

        return (result.result, result.provider_used, result.fallback_occurred)

    def embed_entries(
        self,
        entries: List[Entry],
        show_progress: bool = False,
        preferred_provider: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Embed entries and store in ChromaDB.

        Args:
            entries: List of Entry objects to embed
            show_progress: Whether to print progress (default: False)
            preferred_provider: Explicit provider preference

        Returns:
            Tuple of (provider_used, fallback_occurred)

        Note:
            This is an UPSERT operation - existing entries (by ID) will be updated
        """
        if not entries:
            return ("none", False)

        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        provider_used = None
        fallback_occurred = False

        for i, entry in enumerate(entries):
            if show_progress and (i + 1) % 10 == 0:
                print(f"Embedding entry {i + 1}/{len(entries)}...")

            # Generate embedding with provider transparency
            embedding, provider, fallback = self.embed_text(
                entry.content,
                entity=entry.author,
                preferred_provider=preferred_provider
            )
            
            # Track provider info (use first one as representative)
            if provider_used is None:
                provider_used = provider
                fallback_occurred = fallback

            # Prepare metadata
            metadata = {
                "author": entry.author,
                "type": entry.type,
                "promotion_depth": entry.promotion_depth,
                "trust_weight": entry.trust_weight,
                "timestamp": entry.timestamp.isoformat(),
            }

            # Add optional metadata fields
            if entry.metadata:
                for key, value in entry.metadata.items():
                    # ChromaDB only supports string, int, float, bool
                    if isinstance(value, (str, int, float, bool)):
                        metadata[f"meta_{key}"] = value

            ids.append(entry.id)
            embeddings.append(embedding)
            documents.append(entry.content)
            metadatas.append(metadata)

        # Upsert to ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        if show_progress:
            print(f"✓ Embedded {len(entries)} entries using {provider_used}")
            if fallback_occurred:
                print(f"  (fallback occurred)")

        return (provider_used or "unknown", fallback_occurred)

    def query(
        self,
        query_text: str,
        entity_id: Optional[str] = None,
        scope: Optional[List[str]] = None,
        top_k: int = 20,
        preferred_provider: Optional[str] = None
    ) -> Tuple[List[Tuple[Entry, float]], str, bool]:
        """
        Semantic search for relevant entries.

        Args:
            query_text: Text to search for
            entity_id: Filter by author (entity-specific continuity)
            scope: Optional scope keywords to filter by
            top_k: Number of results to return
            preferred_provider: Explicit provider preference

        Returns:
            Tuple of (entries_with_scores, provider_used, fallback_occurred)
            where entries_with_scores is List of (Entry, relevance_score) tuples
        """
        # Generate query embedding with provider transparency
        query_embedding, provider_used, fallback_occurred = self.embed_text(
            query_text,
            entity=entity_id,
            preferred_provider=preferred_provider
        )

        # Build where filter
        where_filter = {}

        if self.config.strict_entity_filtering and entity_id:
            where_filter["author"] = entity_id

        # Check if collection is empty
        count = self.collection.count()
        if count == 0:
            return ([], provider_used, fallback_occurred)

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            where=where_filter if where_filter else None,
        )

        # Parse results into Entry objects
        entries_with_scores: List[Tuple[Entry, float]] = []

        if not results["ids"] or not results["ids"][0]:
            return (entries_with_scores, provider_used, fallback_occurred)

        for i in range(len(results["ids"][0])):
            entry_id = results["ids"][0][i]
            document = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]

            # Convert distance to similarity score (closer = higher score)
            # ChromaDB uses L2 distance, so we invert it
            relevance_score = 1.0 / (1.0 + distance)

            # Reconstruct Entry
            entry = Entry(
                id=entry_id,
                timestamp=datetime.fromisoformat(metadata["timestamp"]),
                author=metadata["author"],
                type=metadata["type"],  # type: ignore
                content=document,
                promotion_depth=metadata["promotion_depth"],
                trust_weight=metadata["trust_weight"],
                metadata={},
            )

            # Apply scope filtering if provided (post-filter)
            if scope:
                # Check if any scope keyword appears in content (case-insensitive)
                content_lower = entry.content.lower()
                if not any(keyword.lower() in content_lower for keyword in scope):
                    continue

            entries_with_scores.append((entry, relevance_score))

        return (entries_with_scores, provider_used, fallback_occurred)

    def rebuild(
        self,
        entries: List[Entry],
        show_progress: bool = False,
        preferred_provider: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Rebuild vector store from scratch.

        Args:
            entries: List of all entries from canonical log
            show_progress: Whether to print progress
            preferred_provider: Explicit provider preference

        Returns:
            Tuple of (provider_used, fallback_occurred)

        This clears the existing collection and re-embeds all entries.
        """
        if show_progress:
            print("Rebuilding vector store...")

        # Clear existing collection
        self.client.delete_collection("relational_memory")
        self.collection = self.client.create_collection(
            name="relational_memory",
            metadata={"description": "Entity-specific relational memory entries"}
        )

        # Re-embed all entries
        provider_used, fallback_occurred = self.embed_entries(
            entries,
            show_progress=show_progress,
            preferred_provider=preferred_provider
        )

        if show_progress:
            print(f"✓ Vector store rebuilt with {len(entries)} entries")

        return (provider_used, fallback_occurred)

    def get_stats(self) -> dict:
        """
        Get statistics about the vector store and provider registry.

        Returns:
            Dictionary with stats (count, authors, providers, etc.)
        """
        count = self.collection.count()

        # Get provider statistics
        provider_stats = self.provider_registry.get_statistics()

        if count == 0:
            return {
                "total_entries": 0,
                "authors": [],
                "provider_registry": provider_stats,
            }

        # Get all entries to compute stats
        all_results = self.collection.get(include=["metadatas"])

        authors = set()
        if all_results["metadatas"]:
            for metadata in all_results["metadatas"]:
                authors.add(metadata["author"])

        return {
            "total_entries": count,
            "authors": sorted(list(authors)),
            "provider_registry": provider_stats,
        }

    def reset(self) -> None:
        """Delete all data from the vector store (use with caution!)"""
        self.client.delete_collection("relational_memory")
        self.collection = self.client.create_collection(
            name="relational_memory",
            metadata={"description": "Entity-specific relational memory entries"}
        )
