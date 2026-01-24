#!/usr/bin/env python3
"""
Inspect ChromaDB vector store directly.

This script provides programmatic access to explore the vector space,
view embeddings, and understand the structure of the vector store.

Usage:
    python inspect_vector_store.py [vector_store_path] [--by-author] [--stats]

Examples:
    python inspect_vector_store.py
    python inspect_vector_store.py .relational/vector_store --by-author
    python inspect_vector_store.py --stats
"""
import argparse
import chromadb
from pathlib import Path
from collections import defaultdict


def get_stats(collection):
    """Get statistics about the collection."""
    results = collection.get(include=["metadatas"])

    stats = {
        "total_entries": len(results["ids"]),
        "by_author": defaultdict(int),
        "by_type": defaultdict(int),
        "by_promotion_depth": defaultdict(int),
    }

    for metadata in results["metadatas"]:
        stats["by_author"][metadata.get("author", "unknown")] += 1
        stats["by_type"][metadata.get("type", "unknown")] += 1
        stats["by_promotion_depth"][metadata.get("promotion_depth", 0)] += 1

    return stats


def print_stats(stats):
    """Print statistics in a formatted way."""
    print("\n" + "=" * 80)
    print("VECTOR STORE STATISTICS")
    print("=" * 80)

    print(f"\nTotal Entries: {stats['total_entries']}")

    print("\nBy Author:")
    for author, count in sorted(stats["by_author"].items()):
        percentage = (count / stats["total_entries"]) * 100
        print(f"  {author}: {count} ({percentage:.1f}%)")

    print("\nBy Type:")
    for mem_type, count in sorted(stats["by_type"].items()):
        percentage = (count / stats["total_entries"]) * 100
        print(f"  {mem_type}: {count} ({percentage:.1f}%)")

    print("\nBy Promotion Depth:")
    for depth, count in sorted(stats["by_promotion_depth"].items()):
        percentage = (count / stats["total_entries"]) * 100
        print(f"  Depth {depth}: {count} ({percentage:.1f}%)")


def inspect_by_author(collection):
    """Inspect entries grouped by author."""
    results = collection.get(include=["metadatas", "documents"])

    # Group by author
    by_author = defaultdict(list)
    for entry_id, metadata, document in zip(
        results["ids"], results["metadatas"], results["documents"]
    ):
        author = metadata.get("author", "unknown")
        by_author[author].append({
            "id": entry_id,
            "metadata": metadata,
            "document": document,
        })

    # Display by author
    for author, entries in sorted(by_author.items()):
        print("\n" + "=" * 80)
        print(f"Author: {author} ({len(entries)} entries)")
        print("=" * 80 + "\n")

        for i, entry in enumerate(entries, 1):
            print(f"{i}. ID: {entry['id'][:16]}...")
            print(f"   Type: {entry['metadata'].get('type', 'N/A')}")
            print(f"   Timestamp: {entry['metadata'].get('timestamp', 'N/A')}")
            print(f"   Promotion Depth: {entry['metadata'].get('promotion_depth', 'N/A')}")
            print(f"   Trust Weight: {entry['metadata'].get('trust_weight', 'N/A')}")

            # Extract title from document (first line after ##)
            doc_lines = entry["document"].split("\n")
            title = doc_lines[0] if doc_lines else "No title"
            if title.startswith("## "):
                title = title[3:]  # Remove "## "
            print(f"   Title: {title[:70]}...")
            print()


def inspect_all(collection, limit=10):
    """Inspect first N entries from the collection."""
    results = collection.get(limit=limit, include=["metadatas", "documents"])

    print("\n" + "=" * 80)
    print(f"FIRST {limit} ENTRIES")
    print("=" * 80 + "\n")

    for i, (entry_id, metadata, document) in enumerate(
        zip(results["ids"], results["metadatas"], results["documents"]), 1
    ):
        print(f"Entry {i}:")
        print(f"  ID: {entry_id[:16]}...")
        print(f"  Author: {metadata.get('author', 'N/A')}")
        print(f"  Type: {metadata.get('type', 'N/A')}")
        print(f"  Timestamp: {metadata.get('timestamp', 'N/A')}")
        print(f"  Promotion Depth: {metadata.get('promotion_depth', 'N/A')}")
        print(f"  Trust Weight: {metadata.get('trust_weight', 'N/A')}")
        print(f"  Content (first 100 chars): {document[:100]}...")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect ChromaDB vector store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inspect_vector_store.py
  python inspect_vector_store.py .relational/vector_store --by-author
  python inspect_vector_store.py --stats
        """
    )
    parser.add_argument(
        "vector_store_path",
        nargs="?",
        default=".relational/vector_store",
        help="Path to vector store directory (default: .relational/vector_store)"
    )
    parser.add_argument(
        "--by-author",
        action="store_true",
        help="Group entries by author"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics only"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of entries to show (default: 10)"
    )

    args = parser.parse_args()

    # Initialize ChromaDB client
    print(f"Inspecting vector store at: {args.vector_store_path}")
    client = chromadb.PersistentClient(path=args.vector_store_path)

    # List collections
    collections = client.list_collections()
    print(f"Collections: {len(collections)}\n")

    if not collections:
        print("No collections found!")
        return

    # Inspect each collection
    for collection in collections:
        print(f"Collection: {collection.name}")
        print(f"ID: {collection.id}")
        print(f"Total entries: {collection.count()}\n")

        # Get embedding dimension
        results = collection.get(limit=1, include=["embeddings"])
        if results["embeddings"]:
            embedding_dim = len(results["embeddings"][0])
            print(f"Embedding dimension: {embedding_dim}\n")

        # Get statistics
        stats = get_stats(collection)

        if args.stats:
            # Show stats only
            print_stats(stats)
        elif args.by_author:
            # Group by author
            inspect_by_author(collection)
        else:
            # Show first N entries
            inspect_all(collection, limit=args.limit)
            print("\nTip: Use --by-author to group by author, or --stats for statistics")


if __name__ == "__main__":
    main()
