#!/bin/bash
# Entrypoint script for Relational State Engine container
# Handles initialization and environment setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Relational State Engine...${NC}"

# Ensure relational state directories exist
if [ ! -d "/app/.relational/state" ]; then
  echo -e "${YELLOW}Creating state directory...${NC}"
  mkdir -p /app/.relational/state
fi

if [ ! -d "/app/.relational/vector_store" ]; then
  echo -e "${YELLOW}Creating vector store directory...${NC}"
  mkdir -p /app/.relational/vector_store
fi

# Check if package is installed
if ! python -c "import relational_engine" 2>/dev/null; then
  echo -e "${RED}ERROR: relational_engine package not installed${NC}"
  echo -e "${YELLOW}Installing package in editable mode...${NC}"
  pip install -e /app
fi

# Auto-initialize if requested (via environment variable)
if [ "${AUTO_INIT:-false}" = "true" ]; then
  echo -e "${GREEN}Auto-initializing relational engine...${NC}"
  if relational init; then
    echo -e "${GREEN}✓ Initialization complete${NC}"
  else
    echo -e "${YELLOW}⚠ Initialization failed (may already be initialized)${NC}"
  fi
fi

# Download sentence-transformers model on first run if using local embeddings
if [ "${RELATIONAL_EMBEDDING_PROVIDER:-local}" = "local" ]; then
  echo -e "${YELLOW}Checking sentence-transformers model...${NC}"
  python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" 2>/dev/null && \
    echo -e "${GREEN}✓ Model ready${NC}" || \
    echo -e "${YELLOW}Downloading model (this may take a minute on first run)...${NC}"
fi

# Display environment info
echo -e "${GREEN}Environment:${NC}"
echo "  - Embedding provider: ${RELATIONAL_EMBEDDING_PROVIDER:-local}"
echo "  - Python version: $(python --version)"
echo "  - relational CLI: $(which relational || echo 'not in PATH')"

echo -e "${GREEN}Container ready!${NC}"
echo -e "${YELLOW}Run commands with:${NC} docker-compose exec relational relational <command>"
echo ""

# Execute the provided command (or CMD from Dockerfile)
exec "$@"
