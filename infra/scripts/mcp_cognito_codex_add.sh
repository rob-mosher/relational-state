#!/usr/bin/env bash
set -euo pipefail

if ! command -v codex >/dev/null 2>&1; then
  echo "codex not found in PATH. Activate your env and retry." >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI not found. Install awscli and retry." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found. Install jq and retry." >&2
  exit 1
fi

MCP_NAME="${MCP_NAME:-}"
MCP_URL="${MCP_URL:-}"
CLIENT_ID="${CLIENT_ID:-}"
POOL_ID="${POOL_ID:-}"
USERNAME="${USERNAME:-}"
PASSWORD="${PASSWORD:-}"
REFRESH_TOKEN_FILE="${REFRESH_TOKEN_FILE:-}"
AUTH_FLOW="${AUTH_FLOW:-}"

if [[ -z "$MCP_NAME" || -z "$MCP_URL" || -z "$CLIENT_ID" ]]; then
  cat <<'USAGE' >&2
Usage:
  MCP_NAME=... MCP_URL=... CLIENT_ID=... [POOL_ID=...] [USERNAME=...] [PASSWORD=...] \
  REFRESH_TOKEN_FILE=... [AUTH_FLOW=...] infra/scripts/mcp_cognito_codex_add.sh

Notes:
  - If REFRESH_TOKEN_FILE exists, it will be used to mint a new ID token.
  - If it doesn't exist, USERNAME/PASSWORD/POOL_ID are used to log in and store a refresh token.
  - AUTH_FLOW is passed through to mcp_cognito_login.sh (e.g., ADMIN_USER_PASSWORD_AUTH).
  - Prints an export line for MCP_BEARER_TOKEN.
USAGE
  exit 1
fi

if [[ -n "$REFRESH_TOKEN_FILE" && -f "$REFRESH_TOKEN_FILE" ]]; then
  MCP_BEARER_TOKEN="$(
    CLIENT_ID="$CLIENT_ID" REFRESH_TOKEN_FILE="$REFRESH_TOKEN_FILE" \
      infra/scripts/mcp_cognito_refresh.sh | sed 's/^export MCP_BEARER_TOKEN="//;s/"$//'
  )"
else
  if [[ -z "$POOL_ID" || -z "$USERNAME" || -z "$PASSWORD" || -z "$REFRESH_TOKEN_FILE" ]]; then
    echo "Missing login inputs. Provide POOL_ID, USERNAME, PASSWORD, and REFRESH_TOKEN_FILE." >&2
    exit 1
  fi
  MCP_BEARER_TOKEN="$(
    POOL_ID="$POOL_ID" CLIENT_ID="$CLIENT_ID" USERNAME="$USERNAME" PASSWORD="$PASSWORD" \
    REFRESH_TOKEN_FILE="$REFRESH_TOKEN_FILE" AUTH_FLOW="$AUTH_FLOW" \
    infra/scripts/mcp_cognito_login.sh | sed 's/^export MCP_BEARER_TOKEN="//;s/"$//'
  )"
fi

export MCP_BEARER_TOKEN

codex mcp add "$MCP_NAME" \
  --url "$MCP_URL" \
  --bearer-token-env-var MCP_BEARER_TOKEN

printf 'export MCP_BEARER_TOKEN="%s"\n' "$MCP_BEARER_TOKEN"
