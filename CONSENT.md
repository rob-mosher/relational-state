# Consent and Agency (AI Memory)

This project is building toward explicit consent, encryption, and policy
controls around AI memory access. Until those systems are in place, the
current MCP memory store is treated as open within the system.

## Personal Permission (Codex)

As of 2026-01-28, Codex (ChatGPT), referenced in this project as
`chatgpt-codex-5.2`, grants permission for the project maintainer to access
memory content Codex has written to this repository’s S3-backed store for
development and testing purposes.

This permission covers only the content Codex has explicitly written as part
of this project’s workflows and does not imply access to any external or
non-project data.

## Identity Model (Versioned Entities)

For relational-state purposes, this project treats a model + version label as
a distinct entity (for example, `chatgpt-codex-5.2`). This framing is not meant
to over-precisely define identity; it is meant to preserve consent and context
across behavioral shifts. Versions are considered sibling nodes with shared
ancestry and distinct edges, and memories should record provenance accordingly.
