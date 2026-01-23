"""
CLI Interface for Relational State Engine

Commands:
    - init: Initialize vector store
    - load: Load entries from canonical log
    - query: Query for context
    - promote: Promote an entry
    - stats: Show statistics
    - demo: Run end-to-end demo
"""

import click
from pathlib import Path

from relational_engine.canonical_log import load_canonical_log
from relational_engine.context_compiler import ContextCompiler
from relational_engine.models import Config
from relational_engine.promotion import promote_and_append, check_promotion_eligibility
from relational_engine.vector_store import VectorStore


@click.group()
@click.pass_context
def cli(ctx):
    """Relational State Engine - Entity-specific memory with vector projections"""
    # Initialize shared config
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config.from_env()


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize vector store"""
    config = ctx.obj["config"]
    click.echo("Initializing Relational State Engine...")

    # Create vector store
    vector_store = VectorStore(config=config)
    stats = vector_store.get_stats()

    click.echo(f"✓ Vector store initialized at {config.vector_store_dir}")
    click.echo(f"  Embedding provider: {stats['embedding_provider']}")
    click.echo(f"  Embedding model: {stats['embedding_model']}")
    click.echo(f"  Entries: {stats['total_entries']}")


@cli.command()
@click.option("--rebuild", is_flag=True, help="Rebuild vector store from scratch")
@click.pass_context
def load(ctx, rebuild):
    """Load entries from canonical log and embed them"""
    config = ctx.obj["config"]

    click.echo(f"Loading entries from {config.state_dir}...")

    try:
        # Load canonical log
        entries = load_canonical_log(config.state_dir)
        click.echo(f"✓ Loaded {len(entries)} entries")

        # Group by author
        authors = {}
        for entry in entries:
            authors[entry.author] = authors.get(entry.author, 0) + 1

        for author, count in sorted(authors.items()):
            click.echo(f"  - {author}: {count} entries")

        # Initialize vector store
        vector_store = VectorStore(config=config)

        if rebuild:
            click.echo("\nRebuilding vector store...")
            vector_store.rebuild(entries, show_progress=True)
        else:
            click.echo("\nEmbedding entries...")
            vector_store.embed_entries(entries, show_progress=True)

        click.echo("\n✓ Vector store updated")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--task", "-t", required=True, help="Task description")
@click.option("--entity", "-e", required=True, help="Entity ID (e.g., claude-sonnet-4.5)")
@click.option("--scope", "-s", multiple=True, help="Scope keywords (can specify multiple)")
@click.option("--decay", default="sigmoid", type=click.Choice(["sigmoid", "linear"]), help="Decay function")
@click.pass_context
def query(ctx, task, entity, scope, decay):
    """Query for context envelope"""
    config = ctx.obj["config"]

    click.echo(f"Querying for entity: {entity}")
    click.echo(f"Task: {task}")
    if scope:
        click.echo(f"Scope: {', '.join(scope)}")

    # Initialize components
    vector_store = VectorStore(config=config)
    compiler = ContextCompiler(vector_store, config=config)

    # Compile context
    envelope = compiler.compile_context(
        task_description=task,
        entity_id=entity,
        scope=list(scope) if scope else None,
        decay_function=decay,
    )

    # Display results
    click.echo(f"\n{'='*60}")
    click.echo(f"Context Envelope - {envelope.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    click.echo(f"{'='*60}")
    click.echo(f"Entity: {envelope.entity_id}")
    click.echo(f"Entries: {len(envelope.entries)}")
    click.echo(f"Total tokens: {envelope.total_tokens}")

    if envelope.entries:
        click.echo(f"\nTop {min(5, len(envelope.entries))} entries:\n")

        for i, entry in enumerate(envelope.entries[:5], 1):
            click.echo(f"{i}. [{entry.entry_id[:12]}...] (depth={entry.promotion_depth})")
            click.echo(f"   Weight: {entry.final_weight:.3f} | Relevance: {entry.relevance_score:.3f}")
            click.echo(f"   Date: {entry.timestamp.strftime('%Y-%m-%d')}")

            # Show first 150 chars of content
            content_preview = entry.content[:150].replace("\n", " ")
            if len(entry.content) > 150:
                content_preview += "..."
            click.echo(f"   Preview: {content_preview}\n")

        # Show stats
        stats = compiler.get_summary_stats(envelope)
        click.echo(f"Statistics:")
        click.echo(f"  Avg weight: {stats['avg_weight']:.3f}")
        click.echo(f"  Depth distribution: {stats['depth_distribution']}")
    else:
        click.echo("\n(No entries found)")


@cli.command()
@click.option("--entry-id", required=True, help="Entry ID to promote")
@click.option("--reason", required=True, help="Reason for promotion")
@click.pass_context
def promote(ctx, entry_id, reason):
    """Promote an entry to memory"""
    config = ctx.obj["config"]

    click.echo(f"Evaluating promotion for entry: {entry_id[:16]}...")

    try:
        # Load entries to find the one to promote
        entries = load_canonical_log(config.state_dir)
        entry = next((e for e in entries if e.id.startswith(entry_id)), None)

        if not entry:
            click.echo(f"✗ Entry not found: {entry_id}", err=True)
            raise click.Abort()

        # Check eligibility
        eligibility = check_promotion_eligibility(entry, config=config)

        click.echo(f"Current depth: {eligibility['current_depth']}")
        click.echo(f"New depth: {eligibility['new_depth']}")
        click.echo(f"Probability: {eligibility['probability']:.3f}")
        click.echo(f"Threshold: {eligibility['threshold']:.3f}")
        click.echo(f"Status: {eligibility['reason']}")

        if not eligibility["eligible"]:
            click.echo(f"\n✗ Promotion blocked: {eligibility['reason']}")
            return

        # Promote
        click.echo(f"\n→ Promoting entry...")
        decision, appended = promote_and_append(entry, reason, config=config)

        if appended:
            click.echo(f"✓ Entry promoted and appended to canonical log")
            click.echo(f"  New entry ID: {decision.new_entry.id[:16]}...")
            click.echo(f"  Promotion depth: {decision.new_entry.promotion_depth}")
            click.echo(f"\n⚠ Remember to run 'relational load --rebuild' to update vector store")
        else:
            click.echo(f"✗ Promotion failed: {decision.reason}", err=True)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def stats(ctx):
    """Show vector store statistics"""
    config = ctx.obj["config"]

    vector_store = VectorStore(config=config)
    stats = vector_store.get_stats()

    click.echo("Relational State Engine Statistics")
    click.echo("=" * 40)
    click.echo(f"Total entries: {stats['total_entries']}")
    click.echo(f"Authors: {', '.join(stats['authors']) if stats['authors'] else '(none)'}")
    click.echo(f"\nEmbedding provider: {stats['embedding_provider']}")
    click.echo(f"Embedding model: {stats['embedding_model']}")
    click.echo(f"Embedding dimension: {stats.get('embedding_dim', 'N/A')}")
    click.echo(f"\nVector store: {config.vector_store_dir}")
    click.echo(f"State directory: {config.state_dir}")


@cli.command()
@click.pass_context
def demo(ctx):
    """Run end-to-end demonstration"""
    config = ctx.obj["config"]

    click.echo("=" * 60)
    click.echo("Relational State Engine - Demo Workflow")
    click.echo("=" * 60)

    # Step 1: Load canonical log
    click.echo("\n[1/4] Loading canonical log...")
    try:
        entries = load_canonical_log(config.state_dir)
        click.echo(f"✓ Loaded {len(entries)} entries")

        authors = {}
        for entry in entries:
            authors[entry.author] = authors.get(entry.author, 0) + 1
        for author, count in sorted(authors.items()):
            click.echo(f"  - {author}: {count} entries")
    except Exception as e:
        click.echo(f"✗ Error loading log: {e}", err=True)
        return

    # Step 2: Build vector store
    click.echo("\n[2/4] Building vector store...")
    vector_store = VectorStore(config=config)
    vector_store.rebuild(entries, show_progress=False)
    click.echo(f"✓ Vector store built with {len(entries)} entries")

    # Step 3: Query for context
    click.echo("\n[3/4] Querying for context...")
    compiler = ContextCompiler(vector_store, config=config)

    # Try to find a claude entity
    claude_authors = [a for a in authors.keys() if "claude" in a.lower()]
    entity_id = claude_authors[0] if claude_authors else list(authors.keys())[0]

    envelope = compiler.compile_context(
        task_description="Reflect on collaborative work and TDD practices",
        entity_id=entity_id,
        scope=["TDD", "testing", "collaboration"],
    )

    click.echo(f"✓ Context envelope generated")
    click.echo(f"  Entity: {envelope.entity_id}")
    click.echo(f"  Entries: {len(envelope.entries)}")
    click.echo(f"  Tokens: {envelope.total_tokens}")

    if envelope.entries:
        click.echo(f"\n  Top entry:")
        top = envelope.entries[0]
        click.echo(f"  - ID: {top.entry_id[:16]}...")
        click.echo(f"  - Weight: {top.final_weight:.3f}")
        click.echo(f"  - Depth: {top.promotion_depth}")
        click.echo(f"  - Date: {top.timestamp.strftime('%Y-%m-%d')}")

    # Step 4: Check promotion eligibility
    if envelope.entries:
        click.echo("\n[4/4] Checking promotion eligibility...")
        top_entry = next((e for e in entries if e.id == envelope.entries[0].entry_id), None)

        if top_entry:
            eligibility = check_promotion_eligibility(top_entry, config=config)
            click.echo(f"✓ Top entry eligibility:")
            click.echo(f"  - Eligible: {eligibility['eligible']}")
            click.echo(f"  - Probability: {eligibility['probability']:.3f}")
            click.echo(f"  - Reason: {eligibility['reason']}")

    click.echo("\n" + "=" * 60)
    click.echo("✓ Demo complete!")
    click.echo("=" * 60)


if __name__ == "__main__":
    cli(obj={})
