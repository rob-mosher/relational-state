#!/usr/bin/env bash
set -euo pipefail

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI not found. Install awscli and retry." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found. Install jq and retry." >&2
  exit 1
fi

CLIENT_ID="${CLIENT_ID:-}"
REFRESH_TOKEN_FILE="${REFRESH_TOKEN_FILE:-}"

if [[ -z "$CLIENT_ID" || -z "$REFRESH_TOKEN_FILE" ]]; then
  cat <<'USAGE' >&2
Usage:
  CLIENT_ID=... REFRESH_TOKEN_FILE=... infra/scripts/mcp_cognito_refresh.sh

Notes:
  - CLIENT_ID comes from Terraform outputs.
  - REFRESH_TOKEN_FILE should contain a refresh token from mcp_cognito_login.sh.
  - Prints: export MCP_BEARER_TOKEN="..."
USAGE
  exit 1
fi

if [[ ! -f "$REFRESH_TOKEN_FILE" ]]; then
  echo "Refresh token file not found: $REFRESH_TOKEN_FILE" >&2
  exit 1
fi

REFRESH_TOKEN="$(cat "$REFRESH_TOKEN_FILE")"
if [[ -z "$REFRESH_TOKEN" ]]; then
  echo "Refresh token file is empty: $REFRESH_TOKEN_FILE" >&2
  exit 1
fi

AUTH_JSON="$(
  aws cognito-idp initiate-auth \
    --auth-flow REFRESH_TOKEN_AUTH \
    --client-id "$CLIENT_ID" \
    --auth-parameters REFRESH_TOKEN="$REFRESH_TOKEN"
)"

ID_TOKEN="$(printf '%s' "$AUTH_JSON" | jq -r '.AuthenticationResult.IdToken')"

if [[ -z "$ID_TOKEN" || "$ID_TOKEN" == "null" ]]; then
  echo "Failed to refresh ID token. Refresh token may be expired or revoked." >&2
  exit 1
fi

printf 'export MCP_BEARER_TOKEN="%s"\n' "$ID_TOKEN"
