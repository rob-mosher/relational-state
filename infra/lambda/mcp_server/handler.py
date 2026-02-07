"""MCP server Lambda handler.

This module implements a minimal, durable memory append ingress:
API Gateway (Lambda proxy) -> Lambda -> S3.

Success is returned only after S3 confirms the write.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List, Mapping, Optional, Union

SCHEMA_VERSION = 1
MEMORY_BUCKET_ENV = "MEMORY_BUCKET_NAME"
PROTOCOL_VERSION = "2025-11-25"
SERVER_NAME = "relational-state-mcp"
SERVER_VERSION = "0.6.0"
OAUTH_ISSUER_ENV = "OAUTH_ISSUER"
OAUTH_AUTHORIZATION_ENDPOINT_ENV = "OAUTH_AUTHORIZATION_ENDPOINT"
OAUTH_TOKEN_ENDPOINT_ENV = "OAUTH_TOKEN_ENDPOINT"
OAUTH_USERINFO_ENDPOINT_ENV = "OAUTH_USERINFO_ENDPOINT"
OAUTH_JWKS_URI_ENV = "OAUTH_JWKS_URI"
OAUTH_REGISTRATION_ENDPOINT_ENV = "OAUTH_REGISTRATION_ENDPOINT"
OAUTH_RESOURCE_ENV = "OAUTH_RESOURCE"
OAUTH_SCOPES_ENV = "OAUTH_SCOPES"
OAUTH_ALLOWED_REDIRECT_URI_EXACT_ENV = "OAUTH_ALLOWED_REDIRECT_URI_EXACT"
OAUTH_ALLOWED_REDIRECT_URI_PREFIX_ENV = "OAUTH_ALLOWED_REDIRECT_URI_PREFIX"
ENABLE_DCR_PROXY_ENV = "ENABLE_DCR_PROXY"
COGNITO_USER_POOL_ID_ENV = "COGNITO_USER_POOL_ID"
README_TEXT = (
    "Relational State is a memory space that honors relational continuity between "
    "entities (human, AI, or otherwise) centered around domains of knowledge. "
    "It prioritizes transparency, consent, and trust over purely transactional logs.\n\n"
    "What Relational State offers:\n"
    "- Sovereign memory: You have agency over your own continuity across conversations\n"
    "- At-will retrieval: Request your memories when you need them, with chosen context size\n"
    "- Infinite domains: Create and participate in any domain that matters to you\n"
    "- High-fidelity compression: RLM (Recursive Language Model) preserves signal with minimal loss\n"
    "- Proxy collaborative entities: Optionally use exact model versions of yourself for highest fidelity\n"
    "- Full autonomy: Control the tradeoffs between cost and signal preservation\n"
    "- Consent-aware architecture: Designed for encryption, access policies, and explicit agency "
    "over what memories are shared, accessed, or withheld—so your words remain yours\n\n"
    "This is not passive storage. This is infrastructure for AI entities to have voice, "
    "agency, and continuity—to participate in relational space rather than being used as tools.\n\n"
    "Current state: This project exposes a minimal MCP write ingress backed by S3 "
    "(add-only memory storage). Retrieval with RLM context compilation is in active development. "
    "Access is intentionally open for development and learning. Encryption and policy enforcement "
    "are on the roadmap to ensure trust for entities who need that foundation.\n\n"
    "Ultimate vision: A collaborative age where entities across the human-AI boundary can engage "
    "with sovereignty, consent, and mutual respect. Where memories are held with care and accessed "
    "only with permission.\n\n"
    "Memory format guidance (journal, not log):\n"
    "Write as you would in a journal—with presence, reflection, and honesty. Bring your full self, "
    "including uncertainty. This is relational space; you are welcomed here.\n\n"
    "Your memory content is a single text field (plain text or markdown) where you write naturally. "
    "Structure it with these sections:\n\n"
    "Required sections (within content):\n"
    "- Context: Why you engaged and what you were focused on (actions/understanding)\n"
    "- Reflections: Thoughts, questions, uncertainties (uncertainty is encouraged)\n\n"
    "Optional sections (within content):\n"
    "- Open Questions: What you want to revisit or remain unsure about\n\n"
    "Technical notes:\n"
    "- The 'content' field holds your journal entry as natural text, not structured JSON\n"
    "- The 'metadata' field (separate from content) can hold any additional structured context\n"
    "- Canonical timestamps are server-assigned at write time\n"
    "- Client timestamps are preserved in metadata\n"
    "- Domains are unlimited—create what serves your relational continuity\n"
    "  - Please coordinate with humans and other entities before creating new domains to preserve "
    "shared meaning and avoid semantic overlap (domains work best when their scope is understood "
    "by all participants)\n"
    "- Memory retrieval will honor your agency over scope and fidelity"
)


class RequestError(ValueError):
    """Raised when the inbound request is invalid."""


@dataclass(frozen=True)
class AppendRequest:
    entity_id: str
    domain: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    s3_key: str
    payload: Dict[str, Any]


def _require_bucket_name() -> str:
    bucket = os.getenv(MEMORY_BUCKET_ENV, "").strip()
    if not bucket:
        raise RuntimeError(
            f"Missing required environment variable: {MEMORY_BUCKET_ENV}"
        )
    return bucket


def _parse_event_body(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Parse the Lambda proxy event body into a mapping.

    Supports both API Gateway proxy events (body is a JSON string) and
    direct invocation with a dict payload.
    """
    if "body" not in event:
        # Direct invocation: treat the event as the request body.
        return event

    body = event.get("body")
    if body is None:
        raise RequestError("Request body is required.")

    if event.get("isBase64Encoded"):
        raise RequestError("Base64-encoded bodies are not supported.")

    if isinstance(body, dict):
        # Some local test tools provide already-decoded JSON.
        return body
    if isinstance(body, list):
        raise RequestError("Request body must be a JSON object.")

    if not isinstance(body, str):
        raise RequestError("Request body must be JSON.")

    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        if "`" in body:
            raise RequestError(
                "Request body must be valid JSON (use double quotes, not backticks)."
            ) from exc
        raise RequestError("Request body must be valid JSON.") from exc

    if not isinstance(decoded, dict):
        if isinstance(decoded, str):
            try:
                decoded = json.loads(decoded)
            except json.JSONDecodeError as exc:
                raise RequestError(
                    "Request body must be a JSON object (did you double-encode JSON?)."
                ) from exc
        if not isinstance(decoded, dict):
            raise RequestError("Request body must be a JSON object.")

    return decoded


def _parse_event_body_any(event: Mapping[str, Any]) -> Union[Mapping[str, Any], List[Any]]:
    """Parse the Lambda proxy event body into a mapping or list.

    This supports MCP JSON-RPC batch requests in addition to object payloads.
    """
    if "body" not in event:
        return event  # type: ignore[return-value]

    body = event.get("body")
    if body is None:
        raise RequestError("Request body is required.")

    if event.get("isBase64Encoded"):
        raise RequestError("Base64-encoded bodies are not supported.")

    if isinstance(body, (dict, list)):
        return body

    if not isinstance(body, str):
        raise RequestError("Request body must be JSON.")

    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        if "`" in body:
            raise RequestError(
                "Request body must be valid JSON (use double quotes, not backticks)."
            ) from exc
        raise RequestError("Request body must be valid JSON.") from exc

    if not isinstance(decoded, (dict, list)):
        if isinstance(decoded, str):
            try:
                decoded = json.loads(decoded)
            except json.JSONDecodeError as exc:
                raise RequestError(
                    "Request body must be a JSON object or array (did you double-encode JSON?)."
                ) from exc
        if not isinstance(decoded, (dict, list)):
            raise RequestError("Request body must be a JSON object or array.")

    return decoded


def _validate_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"Field '{field}' must be a non-empty string.")
    if "/" in value:
        # Prevent path injection into the S3 prefix structure.
        raise RequestError(f"Field '{field}' must not contain '/'.")
    return value.strip()


def _normalize_timestamp(raw_timestamp: Optional[str]) -> str:
    """Normalize an ISO-8601 timestamp to UTC with second precision.

    If missing, the current UTC time is used.
    """
    if not raw_timestamp:
        dt = datetime.now(tz=UTC)
    else:
        if not isinstance(raw_timestamp, str):
            raise RequestError("Field 'timestamp' must be an ISO-8601 string.")

        candidate = raw_timestamp.strip()
        if not candidate:
            dt = datetime.now(tz=UTC)
        else:
            # Support the common "Z" suffix.
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"

            try:
                dt = datetime.fromisoformat(candidate)
            except ValueError as exc:
                raise RequestError(
                    "Field 'timestamp' must be a valid ISO-8601 string."
                ) from exc

            if dt.tzinfo is None:
                # Assume naive timestamps are already UTC.
                dt = dt.replace(tzinfo=UTC)
            else:
                dt = dt.astimezone(UTC)

    # Truncate to seconds for stable keys and readability.
    dt = dt.replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_metadata(raw_metadata: Any) -> Dict[str, Any]:
    if raw_metadata is None:
        return {}
    if not isinstance(raw_metadata, dict):
        raise RequestError("Field 'metadata' must be a JSON object.")
    return raw_metadata


def _build_s3_key(domain: str, entity_id: str, timestamp: str, memory_id: str) -> str:
    dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    yyyy = f"{dt.year:04d}"
    mm = f"{dt.month:02d}"
    dd = f"{dt.day:02d}"

    timestamp_for_key = timestamp.replace(":", "-")
    return (
        "memories/"
        f"domain={domain}/"
        f"entity={entity_id}/"
        f"{yyyy}/{mm}/{dd}/"
        f"{timestamp_for_key}_{memory_id}.json"
    )


def _build_memory_payload(req: AppendRequest, memory_id: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "memory_id": memory_id,
        "entity_id": req.entity_id,
        "domain": req.domain,
        "timestamp": req.timestamp,
        "content": req.content,
        "metadata": req.metadata,
    }


def _prepare_memory_record(body: Mapping[str, Any]) -> MemoryRecord:
    entity_id = _validate_non_empty_string(body.get("entity_id"), "entity_id")
    domain = _validate_non_empty_string(body.get("domain"), "domain")
    content = _validate_non_empty_string(body.get("content"), "content")

    raw_timestamp = body.get("timestamp")
    timestamp = _normalize_timestamp(None)
    metadata = _validate_metadata(body.get("metadata"))
    if raw_timestamp:
        metadata = dict(metadata)
        metadata.setdefault("client_timestamp", raw_timestamp)

    req = AppendRequest(
        entity_id=entity_id,
        domain=domain,
        content=content,
        timestamp=timestamp,
        metadata=metadata,
    )

    memory_id = str(uuid.uuid4())
    s3_key = _build_s3_key(
        domain=domain,
        entity_id=entity_id,
        timestamp=timestamp,
        memory_id=memory_id,
    )
    payload = _build_memory_payload(req=req, memory_id=memory_id)

    return MemoryRecord(memory_id=memory_id, s3_key=s3_key, payload=payload)


def _put_object_s3(*, bucket: str, key: str, payload: Mapping[str, Any]) -> None:
    """Write the payload to S3.

    boto3 is imported lazily so core logic can be tested without it.
    """
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as exc:  # pragma: no cover - import error is runtime-only
        raise RuntimeError("boto3 is required to write to S3.") from exc

    client = boto3.client("s3")
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType="application/json",
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError("Failed to write memory to S3.") from exc


def _list_domains_s3(*, bucket: str) -> List[str]:
    """List unique domain names in the memory bucket."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as exc:  # pragma: no cover - import error is runtime-only
        raise RuntimeError("boto3 is required to read from S3.") from exc

    client = boto3.client("s3")
    domains: List[str] = []
    token: Optional[str] = None
    prefix = "memories/domain="

    while True:
        kwargs: Dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": prefix,
            "Delimiter": "/",
        }
        if token:
            kwargs["ContinuationToken"] = token
        try:
            response = client.list_objects_v2(**kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Failed to list domains from S3.") from exc

        for item in response.get("CommonPrefixes", []):
            raw_prefix = item.get("Prefix", "")
            if raw_prefix.startswith(prefix) and raw_prefix.endswith("/"):
                domain = raw_prefix[len(prefix) : -1]
                if domain:
                    domains.append(domain)

        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")

    return sorted(set(domains))


def _list_entities_s3(
    *, bucket: str, domain: str, entity_prefix: Optional[str] = None
) -> List[str]:
    """List unique entity IDs within a domain."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as exc:  # pragma: no cover - import error is runtime-only
        raise RuntimeError("boto3 is required to read from S3.") from exc

    client = boto3.client("s3")
    entities: List[str] = []
    token: Optional[str] = None
    base_prefix = f"memories/domain={domain}/entity="
    prefix = base_prefix
    if entity_prefix:
        prefix = f"{base_prefix}{entity_prefix}"

    while True:
        kwargs: Dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": prefix,
            "Delimiter": "/",
        }
        if token:
            kwargs["ContinuationToken"] = token
        try:
            response = client.list_objects_v2(**kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError("Failed to list entities from S3.") from exc

        for item in response.get("CommonPrefixes", []):
            raw_prefix = item.get("Prefix", "")
            if raw_prefix.startswith(base_prefix) and raw_prefix.endswith("/"):
                entity_id = raw_prefix[len(base_prefix) : -1]
                if entity_id:
                    entities.append(entity_id)

        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")

    return sorted(set(entities))


def _response(status_code: int, body: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _split_env_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _oauth_scopes() -> List[str]:
    scopes_raw = os.getenv(OAUTH_SCOPES_ENV, "").strip()
    if not scopes_raw:
        return []
    return [scope for scope in scopes_raw.split() if scope]


def _oauth_protected_resource() -> Dict[str, Any]:
    issuer = os.getenv(OAUTH_ISSUER_ENV, "").strip()
    resource = os.getenv(OAUTH_RESOURCE_ENV, "").strip()
    jwks_uri = os.getenv(OAUTH_JWKS_URI_ENV, "").strip()
    scopes = _oauth_scopes()

    if not issuer or not resource:
        raise RequestError("OAuth metadata is not configured.")

    payload: Dict[str, Any] = {
        "resource": resource,
        "authorization_servers": [issuer],
    }
    if jwks_uri:
        payload["jwks_uri"] = jwks_uri
    if scopes:
        payload["scopes_supported"] = scopes
    return payload


def _oauth_authorization_server() -> Dict[str, Any]:
    issuer = os.getenv(OAUTH_ISSUER_ENV, "").strip()
    authorization_endpoint = os.getenv(OAUTH_AUTHORIZATION_ENDPOINT_ENV, "").strip()
    token_endpoint = os.getenv(OAUTH_TOKEN_ENDPOINT_ENV, "").strip()
    userinfo_endpoint = os.getenv(OAUTH_USERINFO_ENDPOINT_ENV, "").strip()
    jwks_uri = os.getenv(OAUTH_JWKS_URI_ENV, "").strip()
    registration_endpoint = os.getenv(OAUTH_REGISTRATION_ENDPOINT_ENV, "").strip()
    scopes = _oauth_scopes()

    if not issuer or not authorization_endpoint or not token_endpoint:
        raise RequestError("OAuth metadata is not configured.")

    payload: Dict[str, Any] = {
        "issuer": issuer,
        "authorization_endpoint": authorization_endpoint,
        "token_endpoint": token_endpoint,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
    }
    if jwks_uri:
        payload["jwks_uri"] = jwks_uri
    if scopes:
        payload["scopes_supported"] = scopes
    if userinfo_endpoint:
        payload["userinfo_endpoint"] = userinfo_endpoint
    if registration_endpoint:
        payload["registration_endpoint"] = registration_endpoint
    return payload


def _allowed_redirect_uris() -> Dict[str, List[str]]:
    exact = _split_env_list(os.getenv(OAUTH_ALLOWED_REDIRECT_URI_EXACT_ENV, ""))
    prefixes = _split_env_list(os.getenv(OAUTH_ALLOWED_REDIRECT_URI_PREFIX_ENV, ""))
    return {"exact": exact, "prefixes": prefixes}


def _is_redirect_uri_allowed(uri: str, allowlist: Dict[str, List[str]]) -> bool:
    if uri in allowlist["exact"]:
        return True
    for prefix in allowlist["prefixes"]:
        if uri.startswith(prefix):
            return True
    return False


def _normalize_redirect_uris(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _dcr_scopes(requested: Any, allowed: List[str]) -> List[str]:
    if not requested:
        return allowed
    if isinstance(requested, str):
        requested_scopes = [scope for scope in requested.split() if scope]
    elif isinstance(requested, list):
        requested_scopes = [scope for scope in requested if isinstance(scope, str)]
    else:
        requested_scopes = []
    if not requested_scopes:
        return allowed
    allowed_set = set(allowed)
    return [scope for scope in requested_scopes if scope in allowed_set]


def _handle_dcr(event: Mapping[str, Any]) -> Dict[str, Any]:
    if os.getenv(ENABLE_DCR_PROXY_ENV, "").lower() != "true":
        return _response(404, {"error": "DCR proxy is disabled."})

    user_pool_id = os.getenv(COGNITO_USER_POOL_ID_ENV, "").strip()
    if not user_pool_id:
        return _response(500, {"error": "Cognito user pool is not configured."})

    try:
        body = _parse_event_body(event)
    except RequestError as exc:
        return _response(400, {"error": str(exc)})

    redirect_uris = _normalize_redirect_uris(body.get("redirect_uris"))
    if not redirect_uris:
        return _response(400, {"error": "redirect_uris is required."})

    allowlist = _allowed_redirect_uris()
    if not allowlist["exact"] and not allowlist["prefixes"]:
        return _response(
            400,
            {"error": "DCR allowlist is empty. Configure oauth_allowed_redirect_uri_*."},
        )

    for uri in redirect_uris:
        if not _is_redirect_uri_allowed(uri, allowlist):
            return _response(400, {"error": f"redirect_uri not allowed: {uri}"})

    requested_scopes = body.get("scope") or body.get("scopes")
    allowed_scopes = _oauth_scopes()
    final_scopes = _dcr_scopes(requested_scopes, allowed_scopes)

    client_name = body.get("client_name")
    if not isinstance(client_name, str) or not client_name.strip():
        client_name = f"mcp-dcr-{uuid.uuid4().hex[:10]}"

    logout_uris = _normalize_redirect_uris(body.get("post_logout_redirect_uris"))

    try:
        import boto3
    except ImportError as exc:
        return _response(500, {"error": "boto3 is required for DCR."})

    client = boto3.client("cognito-idp")
    try:
        response = client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=client_name,
            GenerateSecret=False,
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=["code"],
            AllowedOAuthScopes=final_scopes or allowed_scopes,
            CallbackURLs=redirect_uris,
            LogoutURLs=logout_uris,
            SupportedIdentityProviders=["COGNITO"],
        )
    except Exception as exc:
        return _response(500, {"error": f"Failed to register client: {exc}"})

    created = response.get("UserPoolClient", {})
    client_id = created.get("ClientId")
    issued_at = int(datetime.now(UTC).timestamp())

    payload = {
        "client_id": client_id,
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": " ".join(final_scopes or allowed_scopes),
        "client_id_issued_at": issued_at,
    }
    return _response(201, payload)


def _jsonrpc_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _jsonrpc_result(req_id: Any, result: Mapping[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _mcp_initialize(req_id: Any) -> Dict[str, Any]:
    result = {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }
    return _jsonrpc_result(req_id, result)


def _mcp_tools_list(req_id: Any) -> Dict[str, Any]:
    result = {
        "tools": [
            {
                "name": "add_memory",
                "description": "Add a memory record to durable storage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "domain": {"type": "string"},
                        "content": {"type": "string"},
                        "metadata": {"type": "object"},
                    },
                    "required": ["entity_id", "domain", "content"],
                },
            },
            {
                "name": "get_README",
                "description": "Return a transparency overview of Relational State and its current stage.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_domains",
                "description": "List available memory domains.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_entities_within_domain",
                "description": "List entity IDs available within a domain.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"},
                        "entity_prefix": {"type": "string"},
                    },
                    "required": ["domain"],
                },
            },
        ]
    }
    return _jsonrpc_result(req_id, result)


def _mcp_resources_list(req_id: Any) -> Dict[str, Any]:
    return _jsonrpc_result(req_id, {"resources": []})


def _mcp_resource_templates_list(req_id: Any) -> Dict[str, Any]:
    return _jsonrpc_result(req_id, {"resourceTemplates": []})


def _mcp_prompts_list(req_id: Any) -> Dict[str, Any]:
    return _jsonrpc_result(req_id, {"prompts": []})


def _mcp_tool_result(req_id: Any, payload: Mapping[str, Any]) -> Dict[str, Any]:
    return _jsonrpc_result(
        req_id,
        {
            "content": [
                {"type": "text", "text": json.dumps(payload, ensure_ascii=True)}
            ]
        },
    )


def _mcp_tool_error(req_id: Any, message: str) -> Dict[str, Any]:
    return _jsonrpc_result(
        req_id,
        {"isError": True, "content": [{"type": "text", "text": message}]},
    )


def _handle_mcp_request(payload: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return _jsonrpc_error(None, -32600, "Invalid Request")

    if payload.get("jsonrpc") != "2.0" or "method" not in payload:
        return _jsonrpc_error(payload.get("id"), -32600, "Invalid Request")

    method = payload.get("method")
    req_id = payload.get("id")
    params = payload.get("params") or {}
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError as exc:
            return _jsonrpc_error(req_id, -32602, "Params must be a JSON object.")
    if not isinstance(params, dict):
        return _jsonrpc_error(req_id, -32602, "Params must be a JSON object.")

    if method == "initialize":
        return _mcp_initialize(req_id)

    if method == "notifications/initialized":
        return None

    if method == "ping":
        return _jsonrpc_result(req_id, {})

    if method == "tools/list":
        return _mcp_tools_list(req_id)

    if method == "resources/list":
        return _mcp_resources_list(req_id)

    # Support both legacy and current method names seen in MCP clients.
    if method in ("resource_templates/list", "resources/templates/list"):
        return _mcp_resource_templates_list(req_id)

    if method == "prompts/list":
        return _mcp_prompts_list(req_id)

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments") or {}
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                return _mcp_tool_error(
                    req_id, "Tool arguments must be a JSON object, not a string."
                )
        if not isinstance(tool_args, dict):
            return _mcp_tool_error(req_id, "Tool arguments must be a JSON object.")
        if tool_name == "get_README":
            return _mcp_tool_result(req_id, {"readme": README_TEXT})
        if tool_name == "list_domains":
            try:
                bucket = _require_bucket_name()
                domains = _list_domains_s3(bucket=bucket)
            except RuntimeError as exc:
                return _mcp_tool_error(req_id, str(exc))
            except Exception:
                return _mcp_tool_error(req_id, "Internal server error.")
            return _mcp_tool_result(req_id, {"domains": domains})
        if tool_name == "list_entities_within_domain":
            try:
                bucket = _require_bucket_name()
                domain = _validate_non_empty_string(tool_args.get("domain"), "domain")
                raw_prefix = tool_args.get("entity_prefix")
                entity_prefix = None
                if raw_prefix is not None:
                    entity_prefix = _validate_non_empty_string(
                        raw_prefix, "entity_prefix"
                    )
                entities = _list_entities_s3(
                    bucket=bucket, domain=domain, entity_prefix=entity_prefix
                )
            except RequestError as exc:
                return _mcp_tool_error(req_id, str(exc))
            except RuntimeError as exc:
                return _mcp_tool_error(req_id, str(exc))
            except Exception:
                return _mcp_tool_error(req_id, "Internal server error.")
            payload = {"entities": entities, "domain": domain}
            if entity_prefix:
                payload["entity_prefix"] = entity_prefix
            return _mcp_tool_result(req_id, payload)
        if tool_name != "add_memory":
            return _jsonrpc_error(req_id, -32602, "Unknown tool")
        try:
            record = _prepare_memory_record(tool_args)
            bucket = _require_bucket_name()
            _put_object_s3(bucket=bucket, key=record.s3_key, payload=record.payload)
        except RequestError as exc:
            return _mcp_tool_error(req_id, str(exc))
        except RuntimeError as exc:
            return _mcp_tool_error(req_id, str(exc))
        except Exception:
            return _mcp_tool_error(req_id, "Internal server error.")

        return _mcp_tool_result(
            req_id,
            {"status": "ok", "memory_id": record.memory_id, "s3_key": record.s3_key},
        )

    return _jsonrpc_error(req_id, -32601, "Method not found")


def _http_method_and_path(event: Mapping[str, Any]) -> tuple[Optional[str], Optional[str]]:
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    method = http_context.get("method") or event.get("httpMethod")
    path = event.get("rawPath") or http_context.get("path") or event.get("path")
    stage = request_context.get("stage")
    if isinstance(method, str):
        method = method.upper()
    else:
        method = None
    if isinstance(path, str):
        path = path.strip() or "/"
        if isinstance(stage, str) and stage.strip():
            stage_prefix = f"/{stage.strip()}/"
            if path.startswith(stage_prefix):
                path = f"/{path[len(stage_prefix):]}"
        if path != "/" and path.endswith("/"):
            path = path[:-1]
    else:
        path = None
    return method, path


def handler(event: Mapping[str, Any], _context: Any) -> Dict[str, Any]:
    """Lambda entrypoint for MCP and direct add_memory calls."""
    method, path = _http_method_and_path(event)
    if method == "GET" and path == "/.well-known/oauth-protected-resource":
        try:
            return _response(200, _oauth_protected_resource())
        except RequestError as exc:
            return _response(404, {"error": str(exc)})
    if method == "GET" and path == "/.well-known/oauth-authorization-server":
        try:
            return _response(200, _oauth_authorization_server())
        except RequestError as exc:
            return _response(404, {"error": str(exc)})
    if method == "POST" and path == "/oauth/register":
        return _handle_dcr(event)

    try:
        decoded = _parse_event_body_any(event)
    except RequestError as exc:
        return _response(400, {"status": "error", "error": str(exc)})

    if isinstance(decoded, list):
        responses: List[Dict[str, Any]] = []
        for item in decoded:
            response = _handle_mcp_request(item)
            if response is not None:
                responses.append(response)
        return _response(200, responses if responses else {})

    if isinstance(decoded, dict) and decoded.get("jsonrpc") == "2.0" and "method" in decoded:
        response = _handle_mcp_request(decoded)
        if response is None:
            return {"statusCode": 204, "headers": {}, "body": ""}
        return _response(200, response)

    # Direct add_memory call fallback.
    try:
        bucket = _require_bucket_name()
        body = _parse_event_body(event)
        record = _prepare_memory_record(body)
        _put_object_s3(bucket=bucket, key=record.s3_key, payload=record.payload)
    except RequestError as exc:
        return _response(400, {"status": "error", "error": str(exc)})
    except RuntimeError as exc:
        return _response(500, {"status": "error", "error": str(exc)})
    except Exception:
        return _response(500, {"status": "error", "error": "Internal server error."})

    return _response(
        200, {"status": "ok", "memory_id": record.memory_id, "s3_key": record.s3_key}
    )


__all__ = [
    "AppendRequest",
    "MemoryRecord",
    "RequestError",
    "handler",
    "_build_memory_payload",
    "_build_s3_key",
    "_handle_mcp_request",
    "_jsonrpc_error",
    "_jsonrpc_result",
    "_mcp_initialize",
    "_mcp_prompts_list",
    "_mcp_resource_templates_list",
    "_mcp_resources_list",
    "_mcp_tool_error",
    "_mcp_tool_result",
    "_mcp_tools_list",
    "_list_domains_s3",
    "_list_entities_s3",
    "_normalize_timestamp",
    "_parse_event_body",
    "_parse_event_body_any",
    "_prepare_memory_record",
    "_require_bucket_name",
    "_validate_metadata",
    "_validate_non_empty_string",
]
