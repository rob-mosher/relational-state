# Future Considerations

This document captures ideas that are intentionally deferred until the system
stabilizes. It exists to avoid premature conventions while keeping a trace of
what may matter later.

## Timezone Support

Timezone handling is intentionally deferred. The current guidance is to store
canonical server timestamps in UTC. If/when client-local time is needed, the
likely pattern is:

- `metadata.client_timestamp`: original ISO-8601 with offset
- `metadata.client_timezone`: IANA timezone name (e.g., `America/New_York`)
