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

POOL_ID="${POOL_ID:-}"
CLIENT_ID="${CLIENT_ID:-}"
USERNAME="${USERNAME:-}"
PASSWORD="${PASSWORD:-}"
REFRESH_TOKEN_FILE="${REFRESH_TOKEN_FILE:-}"

if [[ -z "$POOL_ID" || -z "$CLIENT_ID" || -z "$USERNAME" || -z "$PASSWORD" ]]; then
  cat <<'USAGE' >&2
Usage:
  POOL_ID=... CLIENT_ID=... USERNAME=... PASSWORD=... REFRESH_TOKEN_FILE=... infra/scripts/mcp_cognito_login.sh

Notes:
  - POOL_ID and CLIENT_ID come from Terraform outputs.
  - USERNAME/PASSWORD must exist in the Cognito User Pool.
  - REFRESH_TOKEN_FILE is where the refresh token will be stored.
  - Prints: export MCP_BEARER_TOKEN="..."
USAGE
  exit 1
fi

AUTH_JSON="$(
  aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id "$CLIENT_ID" \
    --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD"
)"

ID_TOKEN="$(printf '%s' "$AUTH_JSON" | jq -r '.AuthenticationResult.IdToken')"
REFRESH_TOKEN="$(printf '%s' "$AUTH_JSON" | jq -r '.AuthenticationResult.RefreshToken')"

if [[ -z "$ID_TOKEN" || "$ID_TOKEN" == "null" ]]; then
  echo "Failed to retrieve ID token. Check credentials and user status." >&2
  exit 1
fi

if [[ -n "$REFRESH_TOKEN_FILE" ]]; then
  if [[ -z "$REFRESH_TOKEN" || "$REFRESH_TOKEN" == "null" ]]; then
    echo "Refresh token not returned. Ensure the app client allows refresh tokens." >&2
    exit 1
  fi
  umask 077
  mkdir -p "$(dirname "$REFRESH_TOKEN_FILE")"
  printf '%s\n' "$REFRESH_TOKEN" >"$REFRESH_TOKEN_FILE"
fi

printf 'export MCP_BEARER_TOKEN="%s"\n' "$ID_TOKEN"
