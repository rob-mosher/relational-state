#!/bin/bash
set -e

echo "Starting Relational State MCP Server..."

# Optional: Auto-initialize if needed
if [ "${AUTO_INIT:-false}" = "true" ]; then
  echo "Auto-initializing relational engine..."
  relational init || true
fi

# Start FastAPI MCP server with hot reloading
exec uvicorn mcp_server.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level info
