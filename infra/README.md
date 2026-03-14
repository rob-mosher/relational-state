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

- The route supports `JWT` or `NONE` (dev-only).
- `JWT`: API Gateway validates bearer tokens (`Authorization: Bearer <token>`).
  - Tokens are issued by Auth0 (Okta). Configure `jwt_issuer` and `jwt_audiences`
    in `terraform.tfvars`.
  - No scopes are required by default; tighten later with `jwt_authorization_scopes`.
- `NONE`: for temporary local dev only.
- For production, use JWT auth.
- Use the `mcp_url` output as-is (it includes a trailing `/` required by API Gateway routing).
- If you see `429`, consider setting `throttling_burst_limit` and
  `throttling_rate_limit` in tfvars to explicit dev-friendly values.

Pick one auth path below:

### Via JWT (Auth0)

Use this when you want bearer tokens. Requires an Auth0 tenant with an
Application and API configured.

#### Auth0 Setup

1. **Create an Auth0 tenant** at [auth0.com](https://auth0.com) (or use an existing one).

2. **Create an Auth0 API** (Resource Server):
   - Name: `Relational State MCP` (or your preference)
   - Identifier (audience): your MCP URL or a logical URI (e.g., `https://mcp.example.com/`)
   - Signing algorithm: RS256

3. **Create an Auth0 Application** for Claude.ai (browser, OAuth + PKCE):
   - Type: Single Page Application
   - Allowed Callback URLs: `https://claude.ai/api/mcp/auth_callback`, `https://claude.com/api/mcp/auth_callback`
   - Allowed Logout URLs: `https://claude.ai/`, `https://claude.com/`
   - Allowed Web Origins: `https://claude.ai`, `https://claude.com`
   - Under Advanced Settings > Grant Types, ensure "Authorization Code" is enabled

4. **Enable Device Authorization Grant** (for Claude Code / TUI clients):
   - In the same Application (or a separate Native application), go to
     Advanced Settings > Grant Types and enable "Device Code"
   - In your Auth0 tenant settings, ensure the Device Code grant is enabled

5. **Create a test user** in Auth0 (Authentication > Database > Username-Password-Authentication).

#### Terraform Configuration

Update your `terraform.tfvars`:

```hcl
api_authorization_type = "JWT"

jwt_issuer    = "https://YOUR_TENANT.auth0.com/"
jwt_audiences = ["YOUR_AUTH0_API_IDENTIFIER"]

oauth_issuer                        = "https://YOUR_TENANT.auth0.com/"
oauth_authorization_endpoint        = "https://YOUR_TENANT.auth0.com/authorize"
oauth_token_endpoint                = "https://YOUR_TENANT.auth0.com/oauth/token"
oauth_userinfo_endpoint             = "https://YOUR_TENANT.auth0.com/userinfo"
oauth_jwks_uri                      = "https://YOUR_TENANT.auth0.com/.well-known/jwks.json"
oauth_device_authorization_endpoint = "https://YOUR_TENANT.auth0.com/oauth/device/code"
```

Apply:

```bash
terraform -chdir=infra/terraform plan -var-file="terraform.tfvars"
terraform -chdir=infra/terraform apply -var-file="terraform.tfvars"
```

#### Connect Claude.ai (Browser)

1. Get your MCP URL:

```bash
terraform -chdir=infra/terraform output -raw mcp_url
```

2. In Claude.ai, go to Settings > Integrations > MCP Servers.
3. Add your MCP URL.
4. Claude.ai will discover OAuth endpoints automatically via
   `/.well-known/oauth-authorization-server`.
5. You'll be redirected to Auth0 to log in.
6. After login, Claude.ai can access your MCP server.

#### Connect Claude Code (TUI)

Claude Code uses HTTP transport with bearer tokens. You can obtain a token
from Auth0 and register the MCP server:

```bash
MCP_URL="$(terraform -chdir=infra/terraform output -raw mcp_url)"

# Option 1: Register per-project (local scope, default)
claude mcp add --transport http relational-state "$MCP_URL" \
  --header "Authorization: Bearer $TOKEN"

# Option 2: Register globally (user scope, available across all projects)
claude mcp add --transport http relational-state "$MCP_URL" \
  --header "Authorization: Bearer $TOKEN" \
  --scope user

# Verify registration
claude mcp list
claude mcp get relational-state
```

#### How It Works

When an OAuth client connects:
1. Fetches `/.well-known/oauth-protected-resource` to discover the OAuth server
2. Fetches `/.well-known/oauth-authorization-server` for endpoint URLs
3. Redirects you to Auth0 for login (authorization code + PKCE)
4. Exchanges authorization code for tokens
5. Uses JWT bearer tokens to call your MCP server

The server also advertises the device authorization grant when configured,
enabling CLI/TUI clients to authenticate without a browser redirect.

#### OAuth Metadata Endpoints

This MCP server exposes:

- `GET /.well-known/oauth-protected-resource`
- `GET /.well-known/oauth-authorization-server`

### Via NONE (dev-only)

Only use this for temporary local development. This disables authentication;
do not expose the endpoint publicly and do not use in production.

## MCP Tools

The MCP server exposes four tools:

- `add_memory`
- `get_README`
- `list_topics`
- `list_entities_within_topic`

### add_memory: Request Body

```json
{
  "entity_id": "string",
  "topic": "string",
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

### list_topics

Returns the list of available memory topics found in S3.

### list_entities_within_topic

Returns the list of entity IDs within a given topic.

Optional:

- `entity_prefix`: limit results to entity IDs that start with the prefix.

## Success/Failure Semantics

- Success is returned only after S3 confirms the write.
- If S3 fails, the response is an error and the caller should retry.
- There are no hidden retries.

## Replay Guarantees

Objects are written with lexicographically sortable keys:

```text
memories/topic={topic}/entity={entity_id}/yyyy/mm/dd/{timestamp}_{uuid}.json
```

This enables:

- Efficient prefix listing
- Natural replay order by key
- Append-only durability (with bucket versioning enabled)
