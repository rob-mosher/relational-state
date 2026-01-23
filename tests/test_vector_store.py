"""
Unit tests for vector_store.py

Tests embedding, storage, and semantic search functionality
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from relational_engine.vector_store import VectorStore
from relational_engine.models import Config, Entry


@pytest.fixture
def temp_vector_dir(tmp_path):
    """Create a temporary directory for vector store"""
    vector_dir = tmp_path / "vector_store"
    vector_dir.mkdir()
    yield str(vector_dir)
    # Cleanup handled by tmp_path


@pytest.fixture
def test_config(temp_vector_dir):
    """Create a test configuration"""
    config = Config()
    config.vector_store_dir = temp_vector_dir
    config.embedding_provider = "local"  # Use local for testing (no API costs)
    return config


@pytest.fixture
def vector_store(test_config):
    """Create a VectorStore instance for testing"""
    return VectorStore(config=test_config)


@pytest.fixture
def sample_entries():
    """Create sample entries for testing"""
    return [
        Entry(
            id="entry1",
            timestamp=datetime(2026, 1, 16),
            author="claude-sonnet-4.5",
            type="reflection",
            content="## 2026-01-16: TDD Practice\n\nWe practiced test-driven development "
                    "with Rob. First wrote failing tests, then implemented the code. "
                    "This ensures better code quality and catches bugs early.",
            promotion_depth=0,
            trust_weight=1.0,
        ),
        Entry(
            id="entry2",
            timestamp=datetime(2026, 1, 15),
            author="claude-sonnet-4.5",
            type="event",
            content="## 2026-01-15: Implementing Brightness Pulse\n\nImplemented adaptive "
                    "brightness hover effect for tiles. Dark tiles brighten, bright tiles "
                    "darken. Used luminance formula to determine threshold.",
            promotion_depth=0,
            trust_weight=1.0,
        ),
        Entry(
            id="entry3",
            timestamp=datetime(2026, 1, 10),
            author="rob-mosher",
            type="reflection",
            content="## 2026-01-10: Initial Setup\n\nStarted the relational state project. "
                    "Goal is to maintain AI-human collaboration context across sessions.",
            promotion_depth=0,
            trust_weight=1.0,
        ),
    ]


class TestVectorStoreInit:
    def test_initializes_with_local_embeddings(self, test_config):
        store = VectorStore(config=test_config)
        assert store.config.embedding_provider == "local"
        assert store.embedder is not None
        assert store.embedding_dim == 384  # MiniLM dimension

    def test_initializes_with_default_config(self, temp_vector_dir):
        """Test initialization with default config"""
        config = Config.from_env()
        config.vector_store_dir = temp_vector_dir
        store = VectorStore(config=config)
        assert store.collection is not None

    def test_raises_on_invalid_provider(self, test_config):
        test_config.embedding_provider = "invalid"  # type: ignore
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            VectorStore(config=test_config)


class TestEmbedText:
    def test_embeds_simple_text(self, vector_store):
        text = "Hello world"
        embedding = vector_store.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384  # MiniLM dimension
        assert all(isinstance(x, float) for x in embedding)

    def test_consistent_embeddings(self, vector_store):
        """Same text should produce same embedding"""
        text = "Test consistency"
        emb1 = vector_store.embed_text(text)
        emb2 = vector_store.embed_text(text)

        assert emb1 == emb2

    def test_different_text_different_embeddings(self, vector_store):
        """Different text should produce different embeddings"""
        emb1 = vector_store.embed_text("Hello")
        emb2 = vector_store.embed_text("World")

        assert emb1 != emb2


class TestEmbedEntries:
    def test_embeds_single_entry(self, vector_store, sample_entries):
        entry = sample_entries[0]
        vector_store.embed_entries([entry])

        # Verify stored in ChromaDB
        result = vector_store.collection.get(ids=[entry.id])
        assert len(result["ids"]) == 1
        assert result["ids"][0] == entry.id
        assert result["metadatas"][0]["author"] == "claude-sonnet-4.5"

    def test_embeds_multiple_entries(self, vector_store, sample_entries):
        vector_store.embed_entries(sample_entries)

        # Verify all stored
        stats = vector_store.get_stats()
        assert stats["total_entries"] == 3
        assert set(stats["authors"]) == {"claude-sonnet-4.5", "rob-mosher"}

    def test_upsert_updates_existing_entry(self, vector_store, sample_entries):
        """Embedding same entry twice should update, not duplicate"""
        entry = sample_entries[0]

        # Embed once
        vector_store.embed_entries([entry])
        count1 = vector_store.collection.count()

        # Embed again (should upsert)
        vector_store.embed_entries([entry])
        count2 = vector_store.collection.count()

        assert count1 == count2 == 1

    def test_handles_empty_list(self, vector_store):
        """Embedding empty list should not error"""
        vector_store.embed_entries([])
        assert vector_store.collection.count() == 0


class TestQuery:
    def test_semantic_search_finds_relevant_entry(self, vector_store, sample_entries):
        vector_store.embed_entries(sample_entries)

        # Query about TDD
        results = vector_store.query("Tell me about test-driven development")

        assert len(results) > 0
        # First result should be the TDD entry
        top_entry, score = results[0]
        assert "TDD" in top_entry.content or "test-driven" in top_entry.content
        assert 0.0 < score <= 1.0

    def test_entity_filtering(self, vector_store, sample_entries):
        """Test strict entity filtering"""
        vector_store.embed_entries(sample_entries)

        # Query only for claude-sonnet-4.5 entries
        results = vector_store.query(
            "Tell me about the project",
            entity_id="claude-sonnet-4.5"
        )

        # Should only return claude entries, not rob's entry
        assert len(results) >= 1
        for entry, score in results:
            assert entry.author == "claude-sonnet-4.5"

    def test_scope_filtering(self, vector_store, sample_entries):
        """Test scope keyword filtering"""
        vector_store.embed_entries(sample_entries)

        # Query with scope
        results = vector_store.query(
            "What did we work on?",
            scope=["TDD", "testing"]
        )

        # Should only return entries mentioning TDD/testing
        assert len(results) >= 1
        for entry, score in results:
            content_lower = entry.content.lower()
            assert "tdd" in content_lower or "test" in content_lower

    def test_top_k_limits_results(self, vector_store, sample_entries):
        vector_store.embed_entries(sample_entries)

        # Query with top_k=1
        results = vector_store.query("Tell me about the project", top_k=1)

        assert len(results) <= 1

    def test_empty_query_returns_results(self, vector_store, sample_entries):
        """Even empty/generic queries should return something"""
        vector_store.embed_entries(sample_entries)

        results = vector_store.query("", top_k=5)
        assert len(results) > 0

    def test_query_on_empty_store(self, vector_store):
        """Querying empty store should return empty list"""
        results = vector_store.query("test query")
        assert results == []


class TestRebuild:
    def test_rebuild_clears_and_reloads(self, vector_store, sample_entries):
        # Initial embed
        vector_store.embed_entries(sample_entries[:2])
        assert vector_store.collection.count() == 2

        # Rebuild with all entries
        vector_store.rebuild(sample_entries)
        assert vector_store.collection.count() == 3

        # Verify all entries present
        stats = vector_store.get_stats()
        assert stats["total_entries"] == 3

    def test_rebuild_with_empty_list(self, vector_store):
        """Rebuilding with empty list should clear store"""
        # Add some entries
        entry = Entry(
            id="test",
            timestamp=datetime.now(),
            author="test",
            type="event",
            content="Test",
            promotion_depth=0,
            trust_weight=1.0,
        )
        vector_store.embed_entries([entry])
        assert vector_store.collection.count() == 1

        # Rebuild with empty list
        vector_store.rebuild([])
        assert vector_store.collection.count() == 0


class TestGetStats:
    def test_stats_on_empty_store(self, vector_store):
        stats = vector_store.get_stats()

        assert stats["total_entries"] == 0
        assert stats["authors"] == []
        assert stats["embedding_provider"] == "local"

    def test_stats_with_entries(self, vector_store, sample_entries):
        vector_store.embed_entries(sample_entries)
        stats = vector_store.get_stats()

        assert stats["total_entries"] == 3
        assert set(stats["authors"]) == {"claude-sonnet-4.5", "rob-mosher"}
        assert stats["embedding_dim"] == 384


class TestReset:
    def test_reset_clears_all_data(self, vector_store, sample_entries):
        # Add entries
        vector_store.embed_entries(sample_entries)
        assert vector_store.collection.count() == 3

        # Reset
        vector_store.reset()
        assert vector_store.collection.count() == 0


class TestIntegrationWithRealData:
    """Integration tests using real canonical log data"""

    @pytest.fixture
    def real_vector_store(self, tmp_path):
        """Vector store with default config pointing to real data"""
        config = Config()
        config.vector_store_dir = str(tmp_path / "vector_store")
        # Use real state directory
        config.state_dir = ".relational/state/"
        return VectorStore(config=config)

    def test_embed_real_entries(self, real_vector_store):
        """Test embedding entries from actual .relational/state/ files"""
        from relational_engine.canonical_log import load_canonical_log

        try:
            # Load real entries
            entries = load_canonical_log()

            # Embed first few entries (up to 5)
            entries_to_embed = entries[:5]
            real_vector_store.embed_entries(entries_to_embed)

            # Verify they're stored (should match number we tried to embed)
            stats = real_vector_store.get_stats()
            assert stats["total_entries"] == len(entries_to_embed)
            assert 1 <= stats["total_entries"] <= 5

        except (FileNotFoundError, ValueError):
            pytest.skip("Real canonical log data not available")

    def test_query_real_data(self, real_vector_store):
        """Test querying against real data"""
        from relational_engine.canonical_log import load_canonical_log

        try:
            entries = load_canonical_log()
            real_vector_store.embed_entries(entries)

            # Query about TDD
            results = real_vector_store.query(
                "How did Claude approach test-driven development?",
                entity_id="claude-sonnet-4.5",
                top_k=5
            )

            if results:
                # Should find relevant entries about TDD
                assert len(results) > 0
                top_entry, score = results[0]
                assert score > 0.5  # Should be reasonably relevant

        except (FileNotFoundError, ValueError):
            pytest.skip("Real canonical log data not available")
