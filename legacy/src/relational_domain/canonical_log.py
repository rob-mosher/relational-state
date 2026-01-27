"""
Canonical Log Reader

Parses markdown files from `.relational/state/` into structured Entry objects.

Format:
    ## 2026-01-16: TDD Practice with Issue #141

    [Content paragraphs...]

    ---

    ## 2026-01-16: Batch TDD - Expanding the Fix

    [Content paragraphs...]

    ---

Strategy:
    - Split on \n---\n separator
    - Extract date/title with regex
    - Generate SHA-256 hash from content
    - Infer author from filename (claude-sonnet-4.5.md → claude-sonnet-4.5)
    - Classify type (heuristic: keywords)
    - Set promotion_depth = 0 for all initial entries
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dateutil.parser import parse as parse_date

from relational_domain.models import Entry


# Regex patterns
ENTRY_HEADER_PATTERN = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}):\s+(.+)$", re.MULTILINE)
SEPARATOR_PATTERN = re.compile(r"\n---\n")


def normalize_content(content: str) -> str:
    """Normalize content for consistent hashing (strip extra whitespace)"""
    # Remove leading/trailing whitespace
    content = content.strip()
    # Normalize multiple newlines to double newline
    content = re.sub(r"\n{3,}", "\n\n", content)
    # Normalize spaces (but preserve markdown formatting)
    return content


def generate_entry_id(content: str) -> str:
    """Generate SHA-256 hash from normalized content"""
    normalized = normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def classify_entry_type(content: str) -> str:
    """
    Infer entry type from content keywords

    Heuristic:
        - "Promotion" or "Promote" → promotion
        - "Reflection" or "Reflections" → reflection
        - Default → event
    """
    content_lower = content.lower()

    if "promotion" in content_lower or "promote" in content_lower:
        return "promotion"
    elif "reflection" in content_lower:
        return "reflection"
    else:
        return "event"


def extract_author_from_filename(filepath: Path) -> str:
    """
    Extract entity ID from filename

    Examples:
        claude-sonnet-4.5.md → claude-sonnet-4.5
        rob-mosher.md → rob-mosher
    """
    return filepath.stem  # Remove .md extension


def parse_entry_chunk(chunk: str, author: str, default_timestamp: datetime) -> Optional[Entry]:
    """
    Parse a single entry chunk into an Entry object

    Args:
        chunk: Markdown text for one entry
        author: Entity ID (from filename)
        default_timestamp: Fallback if header parsing fails

    Returns:
        Entry object or None if parsing fails
    """
    chunk = chunk.strip()
    if not chunk:
        return None

    # Extract header with date and title
    header_match = ENTRY_HEADER_PATTERN.search(chunk)

    if header_match:
        date_str, title = header_match.groups()
        try:
            timestamp = parse_date(date_str)
        except (ValueError, TypeError):
            timestamp = default_timestamp
    else:
        # No header found, use default timestamp
        timestamp = default_timestamp

    # Generate ID from content
    entry_id = generate_entry_id(chunk)

    # Classify type
    entry_type = classify_entry_type(chunk)

    # Create Entry
    return Entry(
        id=entry_id,
        timestamp=timestamp,
        author=author,
        type=entry_type,  # type: ignore
        content=chunk,
        promotion_depth=0,  # All initial entries have depth 0
        trust_weight=1.0,   # Default trust
        metadata={}
    )


def load_entries_from_file(filepath: Path) -> List[Entry]:
    """
    Load all entries from a single markdown file

    Args:
        filepath: Path to markdown file

    Returns:
        List of Entry objects

    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file isn't valid UTF-8
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Read file content
    content = filepath.read_text(encoding="utf-8")

    # Extract author from filename
    author = extract_author_from_filename(filepath)

    # Split into chunks on --- separator
    chunks = SEPARATOR_PATTERN.split(content)

    # Parse each chunk
    entries: List[Entry] = []
    default_timestamp = datetime.now()

    for chunk in chunks:
        entry = parse_entry_chunk(chunk, author, default_timestamp)
        if entry:
            entries.append(entry)

    return entries


def load_canonical_log(state_dir: str = ".relational/state/") -> List[Entry]:
    """
    Load all entries from all markdown files in state directory

    Args:
        state_dir: Directory containing relational state files

    Returns:
        List of all Entry objects from all files

    Raises:
        FileNotFoundError: If state directory doesn't exist
    """
    state_path = Path(state_dir)

    if not state_path.exists():
        raise FileNotFoundError(f"State directory not found: {state_path}")

    if not state_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {state_path}")

    # Find all .md files (excluding hidden files and special files)
    md_files = [
        f for f in state_path.glob("*.md")
        if not f.name.startswith(".")
        and not f.name.startswith("_")
        and f.name.lower() not in ["readme.md", "relational-howto.md"]
    ]

    if not md_files:
        raise ValueError(f"No markdown files found in {state_path}")

    # Load entries from all files
    all_entries: List[Entry] = []
    errors: List[tuple[Path, Exception]] = []

    for md_file in md_files:
        try:
            entries = load_entries_from_file(md_file)
            all_entries.extend(entries)
        except Exception as e:
            # Log error but continue with other files
            errors.append((md_file, e))
            print(f"Warning: Failed to load {md_file.name}: {e}")

    if errors and not all_entries:
        # All files failed to load
        raise ValueError(f"Failed to load any entries. Errors: {errors}")

    # Sort by timestamp (oldest first)
    all_entries.sort(key=lambda e: e.timestamp)

    return all_entries


def append_entry_to_log(entry: Entry, state_dir: str = ".relational/state/") -> None:
    """
    Append a new entry to the author's markdown file

    Args:
        entry: Entry to append
        state_dir: Directory containing relational state files

    Raises:
        FileNotFoundError: If state directory doesn't exist
        PermissionError: If file is not writable
    """
    state_path = Path(state_dir)

    if not state_path.exists():
        raise FileNotFoundError(f"State directory not found: {state_path}")

    # Determine filename
    filename = f"{entry.author}.md"
    filepath = state_path / filename

    # Format entry as markdown
    formatted_entry = format_entry_for_append(entry)

    # Append to file (create if doesn't exist)
    with open(filepath, "a", encoding="utf-8") as f:
        # If file is new or doesn't end with separator, add separator first
        if filepath.exists() and filepath.stat().st_size > 0:
            f.write("\n---\n\n")
        f.write(formatted_entry)
        f.write("\n")


def format_entry_for_append(entry: Entry) -> str:
    """
    Format an Entry for appending to markdown log

    Format:
        ## YYYY-MM-DD: [Title or summary]

        [Content]
    """
    # Extract title from content if present, or generate summary
    header_match = ENTRY_HEADER_PATTERN.search(entry.content)

    if header_match:
        # Entry already has proper header
        return entry.content.strip()
    else:
        # Generate header
        date_str = entry.timestamp.strftime("%Y-%m-%d")
        # Use first line of content as title (truncated)
        lines = entry.content.strip().split("\n")
        title = lines[0][:80] + ("..." if len(lines[0]) > 80 else "")

        formatted = f"## {date_str}: {title}\n\n{entry.content.strip()}"
        return formatted
