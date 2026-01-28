# Infra

## Deploy (Terraform)

Terraform lives in `infra/terraform`.

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
cd infra/terraform
cp backend/dev.hcl.example backend/dev.hcl
terraform init -backend-config=backend/dev.hcl
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

For prod, point init at the prod backend (and use prod tfvars/profile):

```bash
cd infra/terraform
cp backend/prod.hcl.example backend/prod.hcl
terraform init -backend-config=backend/prod.hcl -reconfigure
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
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

- The route uses `AWS_IAM` authorization by default.
- Requests must be SigV4 signed with AWS credentials that can invoke the API.
- For temporary local dev, set `api_authorization_type = "NONE"` in tfvars.
- Terraform can optionally create a dedicated caller user and access keys.
- Use `terraform output -raw caller_access_key_id` and `caller_secret_access_key`.
- If you see `403`, set `caller_policy_scope = "stage"` (or `"api"`) in tfvars.
- For production, prefer IAM roles (or JWT auth) and set `create_caller_user = false`.
- Use the `mcp_url` output as-is (it includes a trailing `/` required by API Gateway routing).
- If you see `429`, consider setting `throttling_burst_limit` and
  `throttling_rate_limit` in tfvars to explicit dev-friendly values.

Example SigV4 call using the Terraform-managed caller user (note the trailing slash):

```bash
cd infra/terraform
export AWS_ACCESS_KEY_ID="$(terraform output -raw caller_access_key_id)"
export AWS_SECRET_ACCESS_KEY="$(terraform output -raw caller_secret_access_key)"
export AWS_REGION="us-east-1"
URL="$(terraform output -raw mcp_url)"

curl --fail-with-body \
  --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api" \
  -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"append_memory","arguments":{"entity_id":"rob","domain":"relational-state","content":"Testing append_memory via IAM."}}}' \
  "$URL"
```

## MCP Tools

The MCP server exposes two tools:

- `append_memory`
- `get_README`

### append_memory: Request Body

```json
{
  "entity_id": "string",
  "domain": "string",
  "content": "string",
  "timestamp": "ISO-8601 string",
  "metadata": {
    "tags": ["string"],
    "source": "string",
    "confidence": 0.0
  }
}
```

### append_memory: Success Response

```json
{
  "status": "ok",
  "memory_id": "string",
  "s3_key": "string"
}
```

### append_memory: Failure Response

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
