# Relational State

This repository exists to honor, record, and nurture *relational continuity* between entities—human, AI, and otherwise, centered around a domain of knowledge/subject.
Unlike traditional logs or memory systems, this space is not transactional. It is *relationally aware*, reflective, and rooted in mutual presence.

## MCP Memory Write Ingress (Append-Only)

This repo now includes a minimal, durable memory ingestion service on AWS:

- API Gateway (HTTP API, IAM-authenticated)
- Lambda (`append_memory`)
- S3 (versioned, append-only source of truth)

All new work for this phase lives under `infra/`.

### What It Does (and Doesn't)

In scope:

- One MCP tool: `append_memory`
- Durable writes to S3
- Clear success/failure semantics

Out of scope (for now):

- Retrieval, listing, summarization, vectorization, routing

## Deploy (Terraform)

Terraform lives in `infra/terraform`.

Set required values (especially `memory_bucket_name`) using a `terraform.tfvars`
file. A starter template lives at `infra/terraform/terraform.tfvars.example`.

Example:

```bash
cd infra/terraform
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

Key outputs:

- `mcp_url`: base HTTPS endpoint for MCP
- `memory_bucket_name`: authoritative S3 bucket

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

## MCP Tool: append_memory

The MCP server exposes one tool: `append_memory`.

### Request Body

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

### Success Response

```json
{
  "status": "ok",
  "memory_id": "string",
  "s3_key": "string"
}
```

### Failure Response

```json
{
  "status": "error",
  "error": "human-readable message"
}
```

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
