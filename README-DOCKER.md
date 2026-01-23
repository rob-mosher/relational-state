# Docker Setup for Relational State Engine

Containerized deployment of the Relational State Engine with hot reloading, persistent storage, and native Docker logging.

## Quick Start

```bash
# Build and start the container
docker-compose up -d --build

# Initialize the vector store (first time only)
docker-compose exec relational relational init

# Load entries from canonical log
docker-compose exec relational relational load

# Run a query
docker-compose exec relational relational query \
  --task "Reflect on collaborative work" \
  --entity rob-mosher

# View logs
docker-compose logs -f relational
```

## Architecture

**Development Container Pattern**: The container stays running with source code mounted as a volume. This keeps the 500MB sentence-transformers model loaded in memory for fast iteration.

**Key Features**:
- ✅ **Hot Reloading**: Edit `.py` files, changes reflected immediately
- ✅ **Persistent Storage**: Data survives container restarts via named volumes
- ✅ **Native Logging**: JSON file driver with automatic rotation
- ✅ **Resource Limits**: Prevents runaway memory usage
- ✅ **Multi-stage Build**: Separate development and production images

## Volume Mounts

### Source Code (Hot Reloading)
```yaml
./src/relational_engine:/app/src/relational_engine:ro
```
- **Read-only** mount prevents accidental modification
- Package installed with `pip install -e .` for editable mode
- Changes to `.py` files immediately available on next command

### Persistent Data (Named Volumes)
```yaml
relational-state:/app/.relational/state
relational-vector-store:/app/.relational/vector_store
```
- **Named volumes** persist across container restarts
- Only deleted with `docker-compose down -v` or explicit `docker volume rm`
- Can be backed up and restored

### Tests (Read-Only)
```yaml
./tests:/app/tests:ro
```
- Mounted read-only for running tests in container
- Run with: `docker-compose exec relational pytest tests/ -v`

## Environment Variables

Set in `.env` file or shell environment:

```bash
# Embedding provider (local or openai)
RELATIONAL_EMBEDDING_PROVIDER=local

# OpenAI API key (only needed if using openai provider)
OPENAI_API_KEY=sk-...
```

Example `.env` file:
```env
RELATIONAL_EMBEDDING_PROVIDER=local
# OPENAI_API_KEY=sk-your-key-here
```

## Usage Examples

### Basic Commands

```bash
# Check CLI is accessible
docker-compose exec relational relational --help

# Initialize vector store
docker-compose exec relational relational init

# Load entries
docker-compose exec relational relational load

# Rebuild vector store from scratch
docker-compose exec relational relational load --rebuild

# Query for context
docker-compose exec relational relational query \
  --task "How did we approach TDD?" \
  --entity claude-sonnet-4.5 \
  --scope TDD --scope testing

# Check status
docker-compose exec relational relational stats

# Run demo workflow
docker-compose exec relational relational demo
```

### Development Workflow

```bash
# 1. Start container
docker-compose up -d

# 2. Make changes to source code
# Edit src/relational_engine/cli.py in your editor

# 3. Test changes immediately (hot reloading)
docker-compose exec relational relational query -t "test" -e rob-mosher

# 4. Run tests
docker-compose exec relational pytest tests/ -v

# 5. View logs
docker-compose logs -f relational

# 6. Stop container (data persists)
docker-compose down
```

### Running Tests

```bash
# All tests
docker-compose exec relational pytest tests/ -v

# Specific test file
docker-compose exec relational pytest tests/test_vector_store.py -v

# With coverage
docker-compose exec relational pytest tests/ \
  --cov=relational_engine \
  --cov-report=html

# View coverage report (generated in container)
docker-compose exec relational cat htmlcov/index.html
```

### Integration Test (End-to-End)

```bash
# Full workflow test
docker-compose exec relational sh -c '
  relational init &&
  relational load &&
  relational query --task "Test query" --entity rob-mosher &&
  relational stats
'
```

## Data Management

### Backup Relational State

```bash
# Create backup directory
mkdir -p backups

# Backup state (canonical log)
docker run --rm \
  -v rm-relational-state_relational-state:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/state-$(date +%Y%m%d-%H%M%S).tar.gz /data

# Backup vector store
docker run --rm \
  -v rm-relational-state_relational-vector-store:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/vector-$(date +%Y%m%d-%H%M%S).tar.gz /data

# Backup both together
docker run --rm \
  -v rm-relational-state_relational-state:/state:ro \
  -v rm-relational-state_relational-vector-store:/vector:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/relational-$(date +%Y%m%d-%H%M%S).tar.gz /state /vector
```

### Restore from Backup

```bash
# Stop container first
docker-compose down

# Restore state
docker run --rm \
  -v rm-relational-state_relational-state:/data \
  -v $(pwd)/backups:/backup \
  alpine sh -c "cd /data && tar xzf /backup/state-YYYYMMDD-HHMMSS.tar.gz --strip-components=1"

# Restart container
docker-compose up -d
```

### List and Inspect Volumes

```bash
# List all volumes
docker volume ls

# Inspect specific volume
docker volume inspect rm-relational-state_relational-state

# See volume size and location
docker system df -v
```

### Clean Up

```bash
# Stop container (keeps volumes)
docker-compose down

# Stop and REMOVE volumes (WARNING: deletes all data!)
docker-compose down -v

# Remove specific volume
docker volume rm rm-relational-state_relational-state

# Remove all unused volumes (careful!)
docker volume prune
```

## Logging

### View Logs

```bash
# Tail logs (follow)
docker-compose logs -f relational

# Last 100 lines
docker-compose logs --tail=100 relational

# Since specific time
docker-compose logs --since 2026-01-23T10:00:00 relational

# Since 1 hour ago
docker-compose logs --since 1h relational

# Using docker logs directly
docker logs -f relational-engine
```

### Log Configuration

Configured in `docker-compose.yml`:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"    # Rotate after 10MB
    max-file: "3"      # Keep 3 files (30MB total)
    labels: "service=relational-engine"
```

### Log Location

Logs are stored by Docker on the host:
- **macOS**: `/var/lib/docker/containers/<container-id>/<container-id>-json.log`
- **Linux**: Same path
- **Windows**: `C:\ProgramData\Docker\containers\<container-id>\<container-id>-json.log`

Find container ID:
```bash
docker ps --format '{{.ID}} {{.Names}}'
```

## Hot Reloading

### How It Works

1. **Source code mounted as volume**: `./src/relational_engine:/app/src/relational_engine:ro`
2. **Package installed in editable mode**: `pip install -e .` in Dockerfile
3. **Python imports from mounted directory**: Changes reflected immediately
4. **No rebuild required**: Edit `.py` files and run commands

### What Triggers Hot Reload

- ✅ Edit any `.py` file in `src/relational_engine/`
- ✅ Next `docker-compose exec` command uses updated code
- ✅ Model stays loaded in memory (fast iteration)

### What Requires Rebuild

- ❌ Changes to `requirements.txt` or `pyproject.toml` → `docker-compose build`
- ❌ Changes to `Dockerfile` → `docker-compose build`
- ❌ System dependency changes → `docker-compose build`

### Testing Hot Reload

```bash
# 1. Start container
docker-compose up -d

# 2. Run initial command
docker-compose exec relational relational stats

# 3. Edit src/relational_engine/cli.py
# Add a print statement to the stats command

# 4. Run command again (should see your change)
docker-compose exec relational relational stats
```

## Resource Limits

Configured in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Max 2 CPU cores
      memory: 4G       # Max 4GB RAM
    reservations:
      cpus: '1.0'      # Reserve 1 core
      memory: 2G       # Reserve 2GB
```

### Adjust Limits

Edit `docker-compose.yml` and restart:
```bash
# Edit limits in docker-compose.yml
nano docker-compose.yml

# Restart container
docker-compose down && docker-compose up -d
```

### Monitor Resource Usage

```bash
# Real-time stats
docker stats relational-engine

# All containers
docker stats

# One-time snapshot
docker stats --no-stream
```

## Building for Production

```bash
# Build production image
docker build --target production -t relational-engine:prod .

# Run production container
docker run -d \
  --name relational-prod \
  -v relational-state:/app/.relational/state \
  -v relational-vector-store:/app/.relational/vector_store \
  -e RELATIONAL_EMBEDDING_PROVIDER=local \
  relational-engine:prod

# Or use docker-compose with production override
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs relational

# Check container status
docker-compose ps

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Package Not Found

```bash
# Reinstall package in container
docker-compose exec relational pip install -e /app

# Or rebuild container
docker-compose build --no-cache
```

### Permission Errors

```bash
# Fix permissions on volumes
docker-compose exec relational chown -R $(id -u):$(id -g) /app/.relational
```

### Model Download Fails

```bash
# Manually trigger model download
docker-compose exec relational python -c \
  "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Out of Memory

```bash
# Increase memory limit in docker-compose.yml
# Then restart:
docker-compose down && docker-compose up -d
```

### Hot Reload Not Working

```bash
# Verify volume mount
docker-compose exec relational ls -la /app/src/relational_engine

# Check if package is in editable mode
docker-compose exec relational pip show -f relational-engine

# Reinstall in editable mode
docker-compose exec relational pip install -e /app
```

### Clean Slate

```bash
# Nuclear option: remove everything and start fresh
docker-compose down -v
docker rmi relational-engine:dev
docker volume rm rm-relational-state_relational-state rm-relational-state_relational-vector-store
docker-compose up -d --build
```

## Advanced Usage

### Interactive Shell

```bash
# Python shell with imports available
docker-compose exec relational python

# Bash shell
docker-compose exec relational bash

# Run specific Python script
docker-compose exec relational python -c "from relational_engine import *; print('Hello')"
```

### Custom Docker Compose Files

Create `docker-compose.override.yml` for local overrides:
```yaml
version: '3.8'

services:
  relational:
    environment:
      - DEBUG=true
    volumes:
      - ./my-data:/app/my-data
```

Docker Compose automatically merges override files.

### Multi-Container Setup (Future)

For MCP server integration:
```yaml
version: '3.8'

services:
  relational:
    # ... existing config ...

  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    depends_on:
      - relational
    ports:
      - "8000:8000"
```

## Performance Tips

1. **Keep container running**: Avoid `docker-compose run` for repeated commands (model reload penalty)
2. **Use named volumes**: Faster than bind mounts on some systems
3. **Limit logs**: Default 10MB x 3 files prevents disk bloat
4. **Monitor resources**: Use `docker stats` to watch memory usage
5. **Prune regularly**: `docker system prune` removes unused data

## Security Considerations

1. **Read-only source mounts**: Prevents accidental code modification in container
2. **No exposed ports**: Container only accessible via `docker-compose exec`
3. **Environment secrets**: Use `.env` file (add to `.gitignore`)
4. **Volume permissions**: Ensure proper ownership and permissions
5. **Regular updates**: Rebuild with latest base image: `docker-compose build --pull`

## Next Steps

After Docker setup is working:
1. **MCP Server Integration** - Add MCP service to docker-compose
2. **Health Checks** - Monitor container health
3. **Metrics** - Add Prometheus/Grafana for monitoring
4. **CI/CD** - Automated builds and testing
5. **Kubernetes** - If scaling beyond single server (probably overkill)

---

**Questions or issues?** Check the main [README-ENGINE.md](README-ENGINE.md) or open an issue.

**Impact Above Origin** 🤠
