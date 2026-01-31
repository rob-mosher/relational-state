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

if [[ -z "$POOL_ID" || -z "$CLIENT_ID" || -z "$USERNAME" || -z "$PASSWORD" ]]; then
  cat <<'USAGE' >&2
Usage:
  POOL_ID=... CLIENT_ID=... USERNAME=... PASSWORD=... infra/scripts/mcp_cognito_token.sh

Notes:
  - POOL_ID and CLIENT_ID come from Terraform outputs.
  - USERNAME/PASSWORD must exist in the Cognito User Pool.
  - Prints: export MCP_BEARER_TOKEN="..."
USAGE
  exit 1
fi

ID_TOKEN="$(
  aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id "$CLIENT_ID" \
    --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD" \
  | jq -r '.AuthenticationResult.IdToken'
)"

if [[ -z "$ID_TOKEN" || "$ID_TOKEN" == "null" ]]; then
  echo "Failed to retrieve ID token. Check credentials and user status." >&2
  exit 1
fi

printf 'export MCP_BEARER_TOKEN="%s"\n' "$ID_TOKEN"
