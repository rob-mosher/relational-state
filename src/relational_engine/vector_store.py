"""
Vector Projection Store

Handles embedding of entries and semantic search using ChromaDB.

Features:
- Dual embedding support (local Sentence-transformers or OpenAI)
- Persistent storage in ChromaDB
- Metadata filtering (author, type, promotion_depth, trust_weight)
- Rebuild from canonical log
- Semantic search with reweighting
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from relational_engine.models import Config, Entry


class VectorStore:
    """
    Vector Projection Store for relational memory

    Embeds entries and enables semantic search with metadata filtering.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize vector store

        Args:
            config: Configuration object (defaults to Config.from_env())
        """
        self.config = config or Config.from_env()

        # Initialize embedding model
        self._init_embedding_model()

        # Initialize ChromaDB client
        self._init_chroma_client()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="relational_memory",
            metadata={"description": "Entity-specific relational memory entries"}
        )

    def _init_embedding_model(self) -> None:
        """Initialize the embedding model based on config"""
        if self.config.embedding_provider == "local":
            # Use Sentence-transformers
            self.embedder = SentenceTransformer(self.config.local_embedding_model)
            self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        elif self.config.embedding_provider == "openai":
            # Use OpenAI embeddings
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "OpenAI embeddings requested but 'openai' package not installed. "
                    "Install with: pip install openai"
                )

            # Set API key from config or environment
            api_key = self.config.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                    "or pass via config.openai_api_key"
                )

            self.openai_client = openai.OpenAI(api_key=api_key)
            self.embedder = None  # Not used for OpenAI
            self.embedding_dim = 1536  # text-embedding-3-small dimension
        else:
            raise ValueError(f"Unknown embedding provider: {self.config.embedding_provider}")

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

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for text

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if self.config.embedding_provider == "local":
            # Use Sentence-transformers
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding.tolist()

        elif self.config.embedding_provider == "openai":
            # Use OpenAI API
            response = self.openai_client.embeddings.create(
                model=self.config.openai_embedding_model,
                input=text
            )
            return response.data[0].embedding

        else:
            raise ValueError(f"Unknown embedding provider: {self.config.embedding_provider}")

    def embed_entries(self, entries: List[Entry], show_progress: bool = False) -> None:
        """
        Embed entries and store in ChromaDB

        Args:
            entries: List of Entry objects to embed
            show_progress: Whether to print progress (default: False)

        Note:
            This is an UPSERT operation - existing entries (by ID) will be updated
        """
        if not entries:
            return

        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, entry in enumerate(entries):
            if show_progress and (i + 1) % 10 == 0:
                print(f"Embedding entry {i + 1}/{len(entries)}...")

            # Generate embedding
            embedding = self.embed_text(entry.content)

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
            print(f"✓ Embedded {len(entries)} entries")

    def query(
        self,
        query_text: str,
        entity_id: Optional[str] = None,
        scope: Optional[List[str]] = None,
        top_k: int = 20,
    ) -> List[Tuple[Entry, float]]:
        """
        Semantic search for relevant entries

        Args:
            query_text: Text to search for
            entity_id: Filter by author (entity-specific continuity)
            scope: Optional scope keywords to filter by
            top_k: Number of results to return

        Returns:
            List of (Entry, relevance_score) tuples, sorted by relevance
        """
        # Generate query embedding
        query_embedding = self.embed_text(query_text)

        # Build where filter
        where_filter = {}

        if self.config.strict_entity_filtering and entity_id:
            where_filter["author"] = entity_id

        # Check if collection is empty
        count = self.collection.count()
        if count == 0:
            return []

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            where=where_filter if where_filter else None,
        )

        # Parse results into Entry objects
        entries_with_scores: List[Tuple[Entry, float]] = []

        if not results["ids"] or not results["ids"][0]:
            return entries_with_scores

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

        return entries_with_scores

    def rebuild(self, entries: List[Entry], show_progress: bool = False) -> None:
        """
        Rebuild vector store from scratch

        Args:
            entries: List of all entries from canonical log
            show_progress: Whether to print progress

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
        self.embed_entries(entries, show_progress=show_progress)

        if show_progress:
            print(f"✓ Vector store rebuilt with {len(entries)} entries")

    def get_stats(self) -> dict:
        """
        Get statistics about the vector store

        Returns:
            Dictionary with stats (count, authors, etc.)
        """
        count = self.collection.count()

        if count == 0:
            return {
                "total_entries": 0,
                "authors": [],
                "embedding_provider": self.config.embedding_provider,
                "embedding_model": (
                    self.config.local_embedding_model
                    if self.config.embedding_provider == "local"
                    else self.config.openai_embedding_model
                ),
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
            "embedding_provider": self.config.embedding_provider,
            "embedding_model": (
                self.config.local_embedding_model
                if self.config.embedding_provider == "local"
                else self.config.openai_embedding_model
            ),
            "embedding_dim": self.embedding_dim,
        }

    def reset(self) -> None:
        """Delete all data from the vector store (use with caution!)"""
        self.client.delete_collection("relational_memory")
        self.collection = self.client.create_collection(
            name="relational_memory",
            metadata={"description": "Entity-specific relational memory entries"}
        )
