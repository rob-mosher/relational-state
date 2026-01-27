#!/usr/bin/env bash
set -euo pipefail

# Wrapper to keep compose file under legacy/docker/ while preserving repo-root paths.
exec docker compose -f legacy/docker/compose.yml --project-directory . "$@"
