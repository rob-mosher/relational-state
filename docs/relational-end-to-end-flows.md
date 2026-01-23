# Relational End-to-End Flows (Pre-Alpha)

These diagrams show the full pipeline: authentication, storage, verification, and summarization.

## Flow A: Central Log + Scoped Summarizer
```mermaid
flowchart TD
  A[Model M] --> B[OIDC Auth]
  B --> C[Ingest API]
  C --> D[Normalize + Hash]
  D --> E[Sign Entry]
  E --> F[Store Entry]
  E --> G[Append to Log]
  G --> H[Log Root + Proofs]
  F --> I[Query + Scope]
  H --> I
  I --> J[Verify + Rank]
  J --> K[Summarizer]
  K --> L[Scoped Summary]
  L --> M[Model M]
  
  style A fill:#dfefff,stroke:#6c9cff,stroke-width:1.5px
  style C fill:#e8fff0,stroke:#00a36c,stroke-width:1.5px
  style E fill:#fff0f0,stroke:#cc4444,stroke-width:1.5px
  style G fill:#f5f0ff,stroke:#9c6cff,stroke-width:1.5px
  style H fill:#f5f0ff,stroke:#9c6cff,stroke-width:1.5px
  style J fill:#e8fff0,stroke:#00a36c,stroke-width:1.5px
  style L fill:#fffbe8,stroke:#e0c600,stroke-width:1.5px
```

## Flow B: Distributed Attesters + Retrieval
```mermaid
flowchart TD
  A[Model M] --> B[OIDC Auth]
  B --> C[Entry Store anywhere]
  A --> D[Hash + Signature]
  D --> E[Attester 1]
  D --> F[Attester 2]
  D --> G[Attester 3]
  C --> H[Reader]
  E --> H
  F --> H
  G --> H
  H --> I[Trust Policy + Rank]
  I --> J[Summarize]
  J --> K[Scoped Summary]
  
  style A fill:#dfefff,stroke:#6c9cff,stroke-width:1.5px
  style D fill:#fff0f0,stroke:#cc4444,stroke-width:1.5px
  style E fill:#f5f0ff,stroke:#9c6cff,stroke-width:1.5px
  style F fill:#f5f0ff,stroke:#9c6cff,stroke-width:1.5px
  style G fill:#f5f0ff,stroke:#9c6cff,stroke-width:1.5px
  style I fill:#e8fff0,stroke:#00a36c,stroke-width:1.5px
  style K fill:#fffbe8,stroke:#e0c600,stroke-width:1.5px
```

## Flow C: Encrypted Pointer + Verification + Summarization
```mermaid
flowchart TD
  A[Model M] --> B[Encrypt Entry]
  B --> C[Private Storage]
  B --> D[Hash + Commitment]
  D --> E[Attestation Log]
  C --> F[Reader w/ Keys]
  E --> F
  F --> G[Verify Commitments]
  G --> H[Summarize]
  H --> I[Scoped Summary]
  
  style A fill:#dfefff,stroke:#6c9cff,stroke-width:1.5px
  style B fill:#fff0f0,stroke:#cc4444,stroke-width:1.5px
  style C fill:#f0f0f0,stroke:#666666,stroke-width:1.5px
  style E fill:#f5f0ff,stroke:#9c6cff,stroke-width:1.5px
  style F fill:#e8fff0,stroke:#00a36c,stroke-width:1.5px
  style G fill:#e8fff0,stroke:#00a36c,stroke-width:1.5px
  style I fill:#fffbe8,stroke:#e0c600,stroke-width:1.5px
```

Notes:
- Flow A favors simplicity and a single log.
- Flow B distributes trust across multiple attesters.
- Flow C maximizes privacy with encrypted storage and public commitments.
