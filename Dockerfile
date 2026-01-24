# Multi-stage Dockerfile for Relational State Engine
# Supports both development (with hot reloading) and production deployments

# ============================================================================
# Stage 1: Base image with system and Python dependencies
# ============================================================================
FROM python:3.12-slim AS base

LABEL maintainer="Rob Mosher <rob@robmosher.com>"
LABEL description="Relational State Engine - Entity-specific memory with vector projections"

WORKDIR /app

# Install system dependencies required for sentence-transformers and ChromaDB
# - build-essential: Compiler tools for Python packages with C extensions
# - git: Required by some Python packages during installation
# - curl: Required for Docker healthcheck
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy dependency files
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
# --no-cache-dir: Don't cache pip downloads (reduces image size)
# This layer will be cached unless requirements change
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Development image (with hot reloading support)
# ============================================================================
FROM base AS development

# Copy source code
# This will be overridden by volume mount in docker-compose for hot reloading
COPY src/ /app/src/

# Install package in editable mode for development
# Changes to mounted source code will be immediately reflected
RUN pip install -e .

# Create directories for relational state
# These will typically be mounted as volumes in docker-compose
RUN mkdir -p /app/.relational/state /app/.relational/vector_store

# Copy and set permissions for startup script
COPY docker/start-mcp.sh /app/docker/start-mcp.sh
RUN chmod +x /app/docker/start-mcp.sh

# Set environment defaults
ENV RELATIONAL_EMBEDDING_PROVIDER=local \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose MCP server port
EXPOSE 8000

# Start MCP server (FastAPI with hot reloading)
CMD ["/app/docker/start-mcp.sh"]

# ============================================================================
# Stage 3: Production image (optimized for deployment)
# ============================================================================
FROM base AS production

# Copy source code
COPY src/ /app/src/

# Install package in non-editable mode
RUN pip install .

# Create directories for relational state
RUN mkdir -p /app/.relational/state /app/.relational/vector_store

# Set environment defaults
ENV RELATIONAL_EMBEDDING_PROVIDER=local \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Production command (can be overridden in docker-compose or docker run)
CMD ["relational", "demo"]
