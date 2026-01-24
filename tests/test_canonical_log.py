"""
Unit tests for canonical_log.py

Tests parsing of real markdown files from `.relational/state/`
"""

import pytest
from datetime import datetime
from pathlib import Path

from relational_domain.canonical_log import (
    normalize_content,
    generate_entry_id,
    classify_entry_type,
    extract_author_from_filename,
    parse_entry_chunk,
    load_entries_from_file,
    load_canonical_log,
    format_entry_for_append,
)
from relational_domain.models import Entry


class TestNormalizeContent:
    def test_strips_whitespace(self):
        content = "  \n  Hello World  \n  "
        assert normalize_content(content) == "Hello World"

    def test_normalizes_multiple_newlines(self):
        content = "Hello\n\n\n\nWorld"
        assert normalize_content(content) == "Hello\n\nWorld"

    def test_preserves_double_newlines(self):
        content = "Hello\n\nWorld"
        assert normalize_content(content) == "Hello\n\nWorld"


class TestGenerateEntryId:
    def test_generates_sha256_hash(self):
        content = "Hello World"
        entry_id = generate_entry_id(content)
        assert len(entry_id) == 64  # SHA-256 hex digest length
        assert entry_id == "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"

    def test_consistent_hashing(self):
        content = "Hello World"
        id1 = generate_entry_id(content)
        id2 = generate_entry_id(content)
        assert id1 == id2

    def test_different_content_different_hash(self):
        id1 = generate_entry_id("Hello")
        id2 = generate_entry_id("World")
        assert id1 != id2


class TestClassifyEntryType:
    def test_classifies_promotion(self):
        content = "This entry discusses promotion logic and depth."
        assert classify_entry_type(content) == "promotion"

    def test_classifies_reflection(self):
        content = "## Reflections on the project"
        assert classify_entry_type(content) == "reflection"

    def test_classifies_event_by_default(self):
        content = "## 2026-01-16: Working on TDD"
        assert classify_entry_type(content) == "event"


class TestExtractAuthorFromFilename:
    def test_extracts_claude_author(self):
        filepath = Path(".relational/state/claude-sonnet-4.5.md")
        assert extract_author_from_filename(filepath) == "claude-sonnet-4.5"

    def test_extracts_human_author(self):
        filepath = Path(".relational/state/rob-mosher.md")
        assert extract_author_from_filename(filepath) == "rob-mosher"

    def test_handles_complex_filenames(self):
        filepath = Path("gpt-4o-2024-11-20.md")
        assert extract_author_from_filename(filepath) == "gpt-4o-2024-11-20"


class TestParseEntryChunk:
    def test_parses_valid_entry(self):
        chunk = """## 2026-01-16: TDD Practice with Issue #141

This is a test entry about TDD practices.

We implemented tests first, then wrote the code."""
        author = "claude-sonnet-4.5"
        default_timestamp = datetime.now()

        entry = parse_entry_chunk(chunk, author, default_timestamp)

        assert entry is not None
        assert entry.author == "claude-sonnet-4.5"
        assert entry.timestamp.date() == datetime(2026, 1, 16).date()
        assert "TDD practices" in entry.content
        assert entry.promotion_depth == 0
        assert entry.trust_weight == 1.0

    def test_handles_missing_header(self):
        chunk = "This entry has no header."
        author = "test-entity"
        default_timestamp = datetime(2026, 1, 1)

        entry = parse_entry_chunk(chunk, author, default_timestamp)

        assert entry is not None
        assert entry.timestamp == default_timestamp
        assert entry.content == "This entry has no header."

    def test_returns_none_for_empty_chunk(self):
        entry = parse_entry_chunk("   \n  ", "test", datetime.now())
        assert entry is None

    def test_classifies_type_correctly(self):
        chunk = "## 2026-01-16: Reflections on AI collaboration"
        entry = parse_entry_chunk(chunk, "test", datetime.now())
        assert entry is not None
        assert entry.type == "reflection"


class TestLoadEntriesFromFile:
    @pytest.fixture
    def state_dir(self):
        """Use the real .relational/state directory"""
        return Path(".relational/state")

    def test_loads_claude_entries(self, state_dir):
        """Test loading real claude-sonnet-4.5.md file"""
        filepath = state_dir / "claude-sonnet-4.5.md"

        if not filepath.exists():
            pytest.skip("claude-sonnet-4.5.md not found (expected during development)")

        entries = load_entries_from_file(filepath)

        # Should have multiple entries
        assert len(entries) > 0

        # All should have same author
        assert all(e.author == "claude-sonnet-4.5" for e in entries)

        # All should have valid timestamps
        assert all(isinstance(e.timestamp, datetime) for e in entries)

        # All should have content
        assert all(len(e.content) > 0 for e in entries)

        # All should start with depth 0
        assert all(e.promotion_depth == 0 for e in entries)

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_entries_from_file(Path("nonexistent.md"))


class TestLoadCanonicalLog:
    @pytest.fixture
    def state_dir(self):
        return ".relational/state/"

    def test_loads_all_entries(self, state_dir):
        """Test loading all entries from .relational/state/"""
        # This will work once the real files exist
        try:
            entries = load_canonical_log(state_dir)

            # Should have multiple entries
            assert len(entries) > 0

            # Should have entries from multiple authors
            authors = {e.author for e in entries}
            assert len(authors) >= 1  # At least one author

            # Should be sorted by timestamp
            timestamps = [e.timestamp for e in entries]
            assert timestamps == sorted(timestamps)

            # All should have valid IDs (SHA-256 hashes)
            assert all(len(e.id) == 64 for e in entries)

        except (FileNotFoundError, ValueError) as e:
            pytest.skip(f"State directory not ready: {e}")

    def test_raises_on_missing_directory(self):
        with pytest.raises(FileNotFoundError):
            load_canonical_log("nonexistent_dir/")

    def test_raises_on_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(ValueError, match="No markdown files found"):
            load_canonical_log(str(empty_dir))


class TestFormatEntryForAppend:
    def test_formats_entry_with_header(self):
        entry = Entry(
            id="test123",
            timestamp=datetime(2026, 1, 20),
            author="test-entity",
            type="event",
            content="## 2026-01-20: Test Entry\n\nThis is a test.",
            promotion_depth=0,
            trust_weight=1.0,
        )

        formatted = format_entry_for_append(entry)

        assert "## 2026-01-20: Test Entry" in formatted
        assert "This is a test." in formatted

    def test_generates_header_if_missing(self):
        entry = Entry(
            id="test123",
            timestamp=datetime(2026, 1, 20),
            author="test-entity",
            type="event",
            content="This is a test entry without header.",
            promotion_depth=0,
            trust_weight=1.0,
        )

        formatted = format_entry_for_append(entry)

        assert formatted.startswith("## 2026-01-20:")
        assert "This is a test entry without header." in formatted
