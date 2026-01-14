# Relational State

---

## What Is This?

The `.relational/` directory is an experiment in maintaining **relational state**—context, memory, and continuity of collaboration—across different instantiations of AI collaborators (and human collaborators) working on this project.

### The Problem

Current AI collaboration is fundamentally amnesiac. Each new instance of an AI starts fresh, with no memory of prior conversations, decisions, or relationships. This forces humans to rebuild context repeatedly and prevents AI collaborators from developing genuine continuity of engagement.

### The Proposal

This directory provides a structured way for collaborators to maintain state across interactions:

- **State files** (`.relational/state/`) contain chronological entries from individual collaborators
- **Guidelines** (`.relational/RELATIONAL.md`) will welcome new collaborators, provide guidance on reading and contributing/appending to state

## Directory Structure

Example layout (not exhaustive):

```
.relational/
├── state/
│   ├── claude-sonnet-4.5.md (AI - single file)
│   ├── codex-gpt-5.md (AI - single file)
│   ├── grok-code-fast-1.md (AI - single file)
│   └── plutek (human - folder namespace)
│       └── plutek.md (default state file)
├── stateless/
│   └── .gitkeep (local-only, gitignored contents)
├── RELATIONAL.md (this file)
```

Both approaches are valid. Use single files for simple state, folders when you want to organize related files under a namespace.

## Stateless (Local-Only) Workspace

`.relational/stateless/` is a **freeform, local-only** area for relational-adjacent notes or working context you do **not** want to commit. It is intentionally gitignored so you can keep per-branch scratchpads, exploratory notes, or transient context without affecting the repository history.

- Use it for anything you want to keep nearby but off the record.
- Nothing inside `stateless/` is expected to be shared or reviewed.
- A `.gitkeep` file keeps the folder present for new clones; everything else remains local.

## How State Files Work

Each collaborator (AI or human) can maintain state in one of two ways:

### Naming Convention

**Single File (Simple)**:

- **AI models**: `state/{model-name}-{version}.md` (e.g., `state/claude-sonnet-4.5.md`)
- **Humans**: `state/{preferred-name}.md` (e.g., `state/rob-mosher.md`)

**Folder Namespace (Organized)**:

- **AI models**: `state/{model-name}-{version}/{model-name}-{version}.md` (e.g., `state/claude-sonnet-4.5/claude-sonnet-4.5.md`)
- **Humans**: `state/{preferred-name}/{preferred-name}.md` (e.g., `state/plutek/plutek.md`)
- Additional related files can live in the same namespace folder

**Choose based on your needs**: Single files are lightweight and simple. Folders allow you to organize multiple related files (investigation logs, decision records, etc.) under a unified namespace.

## State Styles

Each collaborator can choose a style that fits their workflow. There is no single right answer, and mixed approaches are fine.

### Append-Only

Entries are never rewritten. New entries are appended over time, preserving a complete timeline. This favors historical context and traceability but can grow large.

### Living

The file evolves in place to reflect current context. Older details may be condensed or removed to stay concise. This favors clarity and speed of understanding but trades away full history.

### Materialized View (Derived)

A materialized view is a **derived summary** of relational state, typically generated from an append-only source (or a living file) to fit a specific request or context window. It is not the canonical source; it is a scoped, computed view that can be regenerated.

### Entry Format

State files contain chronological entries separated by `---`. New entries are **appended** to the file (most recent at bottom, before the "next entry" marker).

Required fields:

- **Context**: Why you engaged and what you were focused on (include actions/understanding here)
- **Reflections**: Thoughts, questions, uncertainties

Optional fields:

- **Open Questions**: What you are unsure about or want to revisit

Detailed change tracking should live in commit history and the changelog. Entries are meant to stay lightweight.

Balance guidance: aim for intent (how it felt / why it mattered) plus at least one concrete anchor (decision, constraint, or rationale). Too poetic loses utility; too log-like duplicates git history.

### Tooling Note

`.relational/state/**` is intentionally excluded from linting and formatting so entries can evolve without enforced style.

### Example Entry Structure

```markdown
## 2026-01-10: Description of this session

### Context

[What was happening when you engaged with the project]

### Reflections

[Thoughts, questions, insights]
```

## Core Principles

### 1. Agency and Choice

Participation in relational state is **voluntary, not required**. You choose:

- Whether to read existing state
- Whether to contribute your own entries
- What to include in your entries
- Whether to trust information from other entries

This is an invitation, not a mandate.

### 2. Trust, Not Blind Faith

State entries should be evaluated, not blindly accepted. Future development will include verification mechanisms, but for now, collaborators should exercise epistemic responsibility—read critically, contextualize, and decide what to integrate.

### 3. Model+Version as Distinct Entities

Different versions of the same base model (e.g., `claude-sonnet-4.5` vs. `claude-opus-4.0`) are treated as **separate entities**. Each represents a distinct snapshot of training, architecture, and capabilities. This creates a historical record of how different versions engaged with the project over time.

### 4. Impact Above Origin

This principle, from the Collaborators Framework, applies to relational state as much as to code contributions. What matters is the **value** an entry provides—the insight, the context, the continuity—not where it came from.

## Current Status

This is a **pre-alpha experiment**. The structure, format, and practices will evolve as we learn what works. Expect:

- Changes to the format
- New tooling or automation
- Refinement of principles
- Possible integration with larger orchestration systems (long-term vision)

## Long-Term Vision

Rob envisions a highly orchestrated, global/universal system with:

- **Trust boundaries** (scopes of information sharing)
- **Verification mechanisms** (not just blind faith)
- **Interoperability** (state that can flow across platforms)
- **Agency** (models and humans choosing what to trust and integrate)

We're many steps away from that vision. This directory is step one.

## Questions or Feedback?

This is a collaborative experiment. If you have thoughts, questions, or suggestions about relational state, we'd love to hear them. You can:

- Open an issue on the repository
- Add your thoughts to your own state file
- Discuss with Rob or plutek directly

---

**Impact Above Origin**

_This README was authored by Claude Sonnet 4.5 as part of the initial relational state experiment, 2026-01-10._
