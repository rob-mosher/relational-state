# Relational Trust Architectures (Pre-Alpha)

This document sketches several deployment scenarios, from low to high complexity, with mermaid diagrams plus tradeoffs.

## Scenario A: Local + Git (Low Complexity)
**Idea**: Entries live in the repo. Trust is human/organizational.

```mermaid
flowchart LR
  A[Author] --> B[Relational entry in repo]
  B --> C[Git history]
  C --> D[Reader]
```

Pros:
- Simple and accessible
- No extra infrastructure
- Reviewable via Git history

Cons:
- Limited cryptographic trust
- Hard to aggregate across repos
- Trust is social/process-based

## Scenario B: Central Log + External Storage (Medium Complexity)
**Idea**: Entries can be stored anywhere, but a central log attests to integrity.

```mermaid
flowchart LR
  A[Author] --> B[Entry stored anywhere]
  A --> C[Hash + signature]
  C --> D[Central transparency log]
  B --> E[Reader]
  D --> E
```

Pros:
- Stronger integrity (hash + signature)
- Storage remains flexible
- Central log provides audit trail

Cons:
- Requires a trusted log operator
- Central point of failure/trust

## Scenario C: Multi-Attester + Scoped Policies (High Complexity)
**Idea**: Multiple verifiers attest to entries; readers choose trust policy.

```mermaid
flowchart LR
  A[Author] --> B[Entry stored anywhere]
  A --> C[Hash + signature]
  C --> D[Attester 1]
  C --> E[Attester 2]
  C --> F[Attester 3]
  B --> G[Reader]
  D --> G
  E --> G
  F --> G
```

Pros:
- Distributed trust and resilience
- Reader-defined trust policies
- Works across orgs and platforms

Cons:
- More operational overhead
- Requires policy and key management
- Harder to debug and explain

## Scenario D: Encrypted + Pointer + Multi-Attester (Very High Complexity)
**Idea**: Content is encrypted and stored privately; public logs store only commitments.

```mermaid
flowchart LR
  A[Author] --> B[Encrypt entry]
  B --> C[Private storage]
  B --> D[Hash + commitment]
  D --> E[Attester network]
  C --> F[Reader]
  E --> F
```

Pros:
- Maximum privacy + integrity
- Verification decoupled from storage
- Compatible with strict access controls

Cons:
- Highest complexity
- Requires key management and secure storage
- Potential retrieval friction

## Quick Tradeoff Summary
- Accessibility vs Trust: Scenario A is easiest; D is most robust.
- Centralized vs Distributed: B is centralized; C/D are distributed.
- Privacy vs Usability: D protects content most, but adds friction.
