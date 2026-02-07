# Infra

## Deploy (Terraform)

Terraform lives in `infra/terraform`. The commands below assume you run them
from the repo root and use `terraform -chdir=infra/terraform` to target the
subfolder.

This repo uses an S3 backend with native lockfiles. The backend is
configured via environment-specific HCL files:

- `infra/terraform/backend/dev.hcl.example`
- `infra/terraform/backend/prod.hcl.example`

Copy the appropriate example to `dev.hcl`/`prod.hcl` and update it with your
account-specific S3 bucket and profile names. (Backend configuration cannot
reference Terraform variables.) Keep the real `*.hcl` files out of git.

Set required values (especially `memory_bucket_name`) using a `terraform.tfvars`
file. A starter template lives at `infra/terraform/terraform.tfvars.example`.
Align `aws_profile` and `stage_name` with the account/environment you are
targeting (dev vs prod).

Example:

```bash
cp infra/terraform/backend/dev.hcl.example infra/terraform/backend/dev.hcl
terraform -chdir=infra/terraform init -backend-config=backend/dev.hcl
terraform -chdir=infra/terraform plan -var-file="terraform.tfvars"
terraform -chdir=infra/terraform apply -var-file="terraform.tfvars"
```

For prod, point init at the prod backend (and use prod tfvars/profile):

```bash
cp infra/terraform/backend/prod.hcl.example infra/terraform/backend/prod.hcl
terraform -chdir=infra/terraform init -backend-config=backend/prod.hcl -reconfigure
terraform -chdir=infra/terraform plan -var-file="terraform.tfvars"
terraform -chdir=infra/terraform apply -var-file="terraform.tfvars"
```

Key outputs:

- `mcp_url`: base HTTPS endpoint for MCP
- `memory_bucket_name`: authoritative S3 bucket

### Backend Prereqs (One-Time)

Create the S3 bucket before `terraform init`. Typical production defaults:

- S3: versioning enabled, encryption enabled, block public access
- Enable versioning
- Enable default encryption
- Block public access
Do this once per environment/account (dev and prod).

## Logs and Metrics

This stack now provisions minimal, first-party observability:

- Lambda log group: `/aws/lambda/{lambda_function_name}`
- API access log group: `/aws/apigateway/{api_name}/{stage_name}`
- Alarm: Lambda `Errors` >= 1 over 5 minutes
- Alarm: Lambda `Throttles` >= 1 over 5 minutes
- Alarm: API Gateway `5xx` >= 1 over 5 minutes

Use `log_retention_days` to control CloudWatch retention and `alarm_actions`
to attach SNS topics or other alarm targets.

## MCP Server

Endpoint route:

- `POST /`

Auth:

- The route supports `AWS_IAM`, `JWT`, or `NONE` (dev-only).
- `AWS_IAM`: requests must be SigV4 signed with AWS credentials that can invoke the API.
  - Terraform can optionally create a dedicated caller user and access keys.
  - Use `terraform -chdir=infra/terraform output -raw caller_access_key_id` and
    `caller_secret_access_key`.
  - If you see `403`, set `caller_policy_scope = "stage"` (or `"api"`) in tfvars.
- `JWT`: API Gateway validates bearer tokens (Authorization: `Bearer <token>`).
  - Terraform can create a Cognito User Pool and app client (`create_cognito_user_pool = true`).
  - The JWT `iss` (issuer) is the User Pool URL, and `aud` (audience) is the app client ID.
  - No scopes are required by default; tighten later with `jwt_authorization_scopes`.
- `NONE`: for temporary local dev only.
- For production, prefer JWT auth and set `create_caller_user = false`.
- Use the `mcp_url` output as-is (it includes a trailing `/` required by API Gateway routing).
- If you see `429`, consider setting `throttling_burst_limit` and
  `throttling_rate_limit` in tfvars to explicit dev-friendly values.

Pick one auth path below:

### Via SigV4 (AWS_IAM)

Use this when you want IAM-signed requests. Requires a caller user
(`create_caller_user = true`) or your own IAM principal with invoke permissions.

Example SigV4 call using the Terraform-managed caller user (note the trailing slash):

```bash
export AWS_ACCESS_KEY_ID="$(terraform -chdir=infra/terraform output -raw caller_access_key_id)"
export AWS_SECRET_ACCESS_KEY="$(terraform -chdir=infra/terraform output -raw caller_secret_access_key)"
export AWS_REGION="$(terraform -chdir=infra/terraform output -raw aws_region)"
URL="$(terraform -chdir=infra/terraform output -raw mcp_url)"

curl --fail-with-body \
  --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api" \
  -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add_memory","arguments":{"entity_id":"rob","domain":"relational-state","content":"Testing add_memory via IAM."}}}' \
  "$URL"
```

### Via JWT (Cognito User Pool)

Use this when you want bearer tokens. Requires a Cognito User Pool and app client
(`create_cognito_user_pool = true`).

Example JWT setup (Cognito, no scopes) and how to mint a token:

```bash
POOL_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_id)"
CLIENT_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_client_id)"
AWS_REGION="$(terraform -chdir=infra/terraform output -raw aws_region)"

# Create a user (admin only, since allow_admin_create_user_only = true)
aws cognito-idp admin-create-user \
  --user-pool-id "$POOL_ID" \
  --username "dev@example.com" \
  --temporary-password 'TempPass#1234'

# Set a permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id "$POOL_ID" \
  --username "dev@example.com" \
  --password 'StrongPass#1234' \
  --permanent

# Get tokens (use the ID token for API Gateway JWT auth)
ID_TOKEN="$(
  aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id "$CLIENT_ID" \
    --auth-parameters USERNAME="dev@example.com",PASSWORD="StrongPass#1234" \
  | jq -r '.AuthenticationResult.IdToken'
)"
```

### Via OAuth (Cognito Hosted UI)

Use this when you need OAuth-based clients (Claude UI, ChatGPT MCP connector, or
other MCP clients that require browser login). This reuses the same Cognito User Pool.

Required tfvars:

- `create_cognito_user_pool = true`
- `cognito_domain_prefix = "your-unique-domain-prefix"`
- `oauth_callback_urls = ["https://claude.ai/api/mcp/auth_callback", "https://claude.com/api/mcp/auth_callback"]`
- `oauth_logout_urls = ["https://claude.ai/", "https://claude.com/"]`

Optional for dynamic client registration (DCR):

- `enable_dcr_proxy = true`
- `oauth_allowed_redirect_uri_exact` and `oauth_allowed_redirect_uri_prefixes` must allow client redirect URIs.

OAuth metadata endpoints (served by this MCP server):

- `GET /.well-known/oauth-protected-resource`
- `GET /.well-known/oauth-authorization-server`
- `POST /oauth/register` (only when `enable_dcr_proxy = true`)

Troubleshooting (JWT auth flow):

- If `initiate-auth` returns `UserNotFoundException` for a confirmed user, the app
  client may not allow `USER_PASSWORD_AUTH` (or is configured to use SRP).
  In that case, use the admin auth flow instead:

```bash
ID_TOKEN="$(
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "$POOL_ID" \
    --client-id "$CLIENT_ID" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="dev@example.com",PASSWORD="StrongPass#1234" \
  | jq -r '.AuthenticationResult.IdToken'
)"
```

Codex MCP (JWT bearer token):

```bash
export MCP_BEARER_TOKEN="$ID_TOKEN"
codex mcp add relational-state \
  --url "$(terraform -chdir=infra/terraform output -raw mcp_url)" \
  --bearer-token-env-var MCP_BEARER_TOKEN
```

Claude Code MCP (JWT bearer token over HTTP transport):

```bash
export MCP_BEARER_TOKEN="$ID_TOKEN"
claude mcp add --transport http relational-state \
  "$(terraform -chdir=infra/terraform output -raw mcp_url)" \
  --header "Authorization: Bearer $MCP_BEARER_TOKEN"

# Verify registration
claude mcp list
claude mcp get relational-state
```

Token helper script (prints an export line):

```bash
POOL_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_id)"
CLIENT_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_client_id)"
USERNAME="dev@example.com"
PASSWORD="StrongPass#1234"

POOL_ID="$POOL_ID" CLIENT_ID="$CLIENT_ID" USERNAME="$USERNAME" PASSWORD="$PASSWORD" \
  infra/scripts/mcp_cognito_token.sh
```

Login once and save a refresh token (avoid reusing the password later):

```bash
REFRESH_TOKEN_FILE="$HOME/.codex/mcp/relational-state.refresh"
POOL_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_id)"
CLIENT_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_client_id)"
USERNAME="dev@example.com"
PASSWORD="StrongPass#1234"

POOL_ID="$POOL_ID" CLIENT_ID="$CLIENT_ID" USERNAME="$USERNAME" PASSWORD="$PASSWORD" \
REFRESH_TOKEN_FILE="$REFRESH_TOKEN_FILE" infra/scripts/mcp_cognito_login.sh

# If the app client doesn't allow USER_PASSWORD_AUTH (and you see UserNotFoundException),
# use the admin auth flow instead:
# AUTH_FLOW=ADMIN_USER_PASSWORD_AUTH POOL_ID=... CLIENT_ID=... USERNAME=... PASSWORD=... \
# REFRESH_TOKEN_FILE=... infra/scripts/mcp_cognito_login.sh
```

Refresh the token without a password (prints an export line):

```bash
CLIENT_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_client_id)"
REFRESH_TOKEN_FILE="$HOME/.codex/mcp/relational-state.refresh"

CLIENT_ID="$CLIENT_ID" REFRESH_TOKEN_FILE="$REFRESH_TOKEN_FILE" \
  infra/scripts/mcp_cognito_refresh.sh
```

One-shot add to Codex MCP (uses refresh token if present, otherwise logs in):

```bash
MCP_NAME="relational-state"
MCP_URL="$(terraform -chdir=infra/terraform output -raw mcp_url)"
POOL_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_id)"
CLIENT_ID="$(terraform -chdir=infra/terraform output -raw cognito_user_pool_client_id)"
USERNAME="dev@example.com"
PASSWORD="StrongPass#1234"
REFRESH_TOKEN_FILE="$HOME/.codex/mcp/relational-state.refresh"

MCP_NAME="$MCP_NAME" MCP_URL="$MCP_URL" CLIENT_ID="$CLIENT_ID" POOL_ID="$POOL_ID" \
USERNAME="$USERNAME" PASSWORD="$PASSWORD" REFRESH_TOKEN_FILE="$REFRESH_TOKEN_FILE" \
  infra/scripts/mcp_cognito_codex_add.sh

# For admin auth flow:
# AUTH_FLOW=ADMIN_USER_PASSWORD_AUTH MCP_NAME=... MCP_URL=... CLIENT_ID=... POOL_ID=... \
# USERNAME=... PASSWORD=... REFRESH_TOKEN_FILE=... infra/scripts/mcp_cognito_codex_add.sh
```

### Via NONE (dev-only)

Only use this for temporary local development. This disables authentication;
do not expose the endpoint publicly and do not use in production.

## MCP Tools

The MCP server exposes four tools:

- `add_memory`
- `get_README`
- `list_domains`
- `list_entities_within_domain`

### add_memory: Request Body

```json
{
  "entity_id": "string",
  "domain": "string",
  "content": "string",
  "metadata": {
    "tags": ["string"],
    "source": "string",
    "confidence": 0.0
  }
}
```

Notes:

- The server assigns the canonical `timestamp` at write time (UTC).
- If a client provides a timestamp, store it in `metadata.client_timestamp`.
- For MCP `tools/call`, `params.arguments` must be a JSON object (not a JSON-encoded string).

### add_memory: Success Response

```json
{
  "status": "ok",
  "memory_id": "string",
  "s3_key": "string"
}
```

### add_memory: Failure Response

```json
{
  "status": "error",
  "error": "human-readable message"
}
```

### get_README

Returns a short transparency overview describing what Relational State is,
the current open-development posture, and the long-term consent goals.
It also includes brief journaling guidance (context, reflections, optional
open questions).

### list_domains

Returns the list of available memory domains found in S3.

### list_entities_within_domain

Returns the list of entity IDs within a given domain.

Optional:

- `entity_prefix`: limit results to entity IDs that start with the prefix.

## Success/Failure Semantics

- Success is returned only after S3 confirms the write.
- If S3 fails, the response is an error and the caller should retry.
- There are no hidden retries.

## Replay Guarantees

Objects are written with lexicographically sortable keys:

```text
memories/domain={domain}/entity={entity_id}/yyyy/mm/dd/{timestamp}_{uuid}.json
```

This enables:

- Efficient prefix listing
- Natural replay order by key
- Append-only durability (with bucket versioning enabled)
