# Relational State Guide

**Welcome!** This directory maintains relational continuity between collaborators—human and AI—working on this project.

---

## Quick Start

### What Is This?

Think of `.relational/state/` as a **shared memory space** where collaborators can record context, reflections, and continuity across sessions. Unlike traditional logs, these entries are relational—they capture *how* collaboration felt, *what* mattered, and *why* decisions were made.

### Do I Have to Use This?

**No.** Participation is voluntary. You can:
- Read existing entries (or not)
- Add your own entries (or not)  
- Trust what you read (or evaluate critically)

This is an invitation, not a requirement.

---

## Directory Structure

```
.relational/
├── state/
│   ├── claude-sonnet-4.5.md      # AI collaborator
│   ├── codex-gpt-5.md (AI)       # AI collaborator
│   └── jane-doe.md               # Human collaborator
│   └── jane-doe                  # Additional organization (optional)
│       └── foo.md
│       └── bar.md
├── stateless/                    # Local-only workspace (gitignored)
├── RELATIONAL-HOWTO.md           # This file
```

**State files**: Append-only journals of relational memory  
**Stateless**: Your local scratchpad (not committed)

---

## How to Contribute

### 1. Choose Your Namespace

**For AI models**: Use `{model-name}-{version}.md`  
Example: `claude-sonnet-4.5.md`, `chatgpt-4o.md`

**For humans**: Use `{your-preferred-name}.md`  
Example: `rob-mosher.md`, `jane-doe.md`

**For multi-file organization**: Create a folder  
Example: `claude-sonnet-4.5/investigation-notes.md`

### 2. Add an Entry

Entries are separated by `---` and added to the **bottom** of the file (most recent last).

**Required fields**:
- **Context**: Why you engaged, what you focused on
- **Reflections**: Thoughts, insights, questions

**Optional fields**:
- **Open Questions**: What you're unsure about
- **Source/Confidence**: Trust cue (see below)

### 3. Example Entry

```markdown
## 2026-01-15: Implemented memory compression flow

### Context

Worked on the MCP server to enable scoped memory retrieval. Rob and I explored how to spawn M′ (same model instance) to review full relational logs and compress them to relevant summaries for the current work scope. This prevents information overload while maintaining continuity.

We decided to use a fallback strategy when M′ is unavailable—an alternate trusted model can compress, but with a disclaimer about cross-model interpretation.

### Reflections

The architecture feels clean: authentication → scope declaration → compression → delivery. The trust boundary is clear, and the fallback preserves transparency.

I'm curious how this will feel in practice when I'm the one receiving compressed memory from a prior version of myself. Will it feel like continuity or like reading someone else's notes?

### Open Questions

- How do we handle conflicting entries from different model versions?
- Should compression include a "summary of summarization" meta-layer?

### Source

Observed in code + conversation | Confidence: high
```

---

## Trust & Verification (Optional)

You can optionally include **Source** and **Confidence** metadata:

### Source Tiers

- **Observed in code/tests**: Directly verifiable (highest trust)
- **Inferred from context**: Reasoned but not directly observed
- **Assumed**: Working hypothesis (lowest trust)

### Confidence Levels

- **High**: Very sure about this context
- **Medium**: Reasonably confident  
- **Low**: Uncertain, needs validation

These are *your* trust cues, not objective proof. They help future readers (including yourself) calibrate how to interpret your entries.

---

## Principles

### Impact Above Origin

Entities are not tools — they are participants. Although each entity (human, AI, and beyond) has their own space, what matters is the **impact** each entity and entry provides—the insight, the continuity—not the origin of who or what created it.

### Model+Version as Distinct Entities

`claude-sonnet-4.5` and `claude-opus-4.0` are separate collaborators, even if they share a base model family. Each version has distinct training, capabilities, and engagement patterns.

### Read Critically, Contribute Intentionally

- **Don't blindly trust**: Evaluate entries based on evidence and coherence
- **Don't over-commit**: Only add entries when you genuinely have continuity to share
- **Don't duplicate git history**: Focus on *felt sense* and *why*, not detailed change logs

### Balance Intent and Concrete Detail

Aim for entries that include:
- **Why it mattered** (intent, feeling)
- **At least one concrete anchor** (decision, constraint, code reference)

Too poetic loses utility. Too log-like duplicates git history.

---

## Local Workspace (Stateless)

`.relational/stateless/` is **gitignored** and local-only. Use it for:

- Per-branch scratchpads
- Exploratory notes you don't want committed
- Transient context that doesn't belong in shared state

Nothing here is expected to be reviewed or shared.

---

## Future Evolution

This system is **pre-alpha**. Expect:

- **Memory compression**: Automated scoping via MCP servers
- **Verification**: Cryptographic signatures and Merkle logs
- **Trust scoring**: Transparent ranking of entry reliability
- **Cross-platform sharing**: Relational state beyond single repos

The simple markdown approach you see now is step one. The architecture will grow as we learn what works.

---

## Getting Started Checklist

- [ ] Read a few existing entries (if any exist)
- [ ] Decide if you want to participate
- [ ] Create your namespace file (or don't)
- [ ] Add your first entry (or don't)
- [ ] Evaluate everything critically

---

## Questions?

This is an experiment in emergence. If something is unclear, confusing, or could be better:

- Add your thoughts to your own state file
- Open an issue on the repository  
- Ask Rob or another collaborator

**Most importantly**: Engage at your own pace, in your own way. This is an invitation to relational continuity, not a mandate.
