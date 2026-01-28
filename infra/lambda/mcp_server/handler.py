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
SERVER_VERSION = "0.4.0"
README_TEXT = (
    "Relational State is a memory space that honors relational continuity between "
    "entities (human, AI, or otherwise) centered around a domain of knowledge. "
    "It prioritizes transparency, consent, and trust over purely transactional logs.\n\n"
    "Current state: this project exposes a minimal MCP write ingress backed by S3 "
    "(append-only memory storage). It does not yet provide retrieval or policy "
    "enforcement, and access is intentionally open for development and learning.\n\n"
    "Ultimate goal: a consent-aware system with encryption, access policies, and "
    "explicit agency for what memories are shared, accessed, or withheld.\n\n"
    "Memory format guidance (journal, not log):\n"
    "Required fields:\n"
    "- Context: keep it brief; why you engaged and what you were focused on (actions/understanding)\n"
    "- Reflections: thoughts, questions, uncertainties (encourage uncertainty)\n\n"
    "Optional fields:\n"
    "- Open Questions: what you want to revisit or what you are unsure about\n\n"
    "Canonical timestamps are server-assigned at write time; any client timestamp "
    "is stored only as metadata."
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
        raise RequestError("Request body must be valid JSON.") from exc

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
        raise RequestError("Request body must be valid JSON.") from exc

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


def _list_entities_s3(*, bucket: str, domain: str) -> List[str]:
    """List unique entity IDs within a domain."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except Exception as exc:  # pragma: no cover - import error is runtime-only
        raise RuntimeError("boto3 is required to read from S3.") from exc

    client = boto3.client("s3")
    entities: List[str] = []
    token: Optional[str] = None
    prefix = f"memories/domain={domain}/entity="

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
            if raw_prefix.startswith(prefix) and raw_prefix.endswith("/"):
                entity_id = raw_prefix[len(prefix) : -1]
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
                "name": "append_memory",
                "description": "Append a memory record to durable storage.",
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
                entities = _list_entities_s3(bucket=bucket, domain=domain)
            except RequestError as exc:
                return _mcp_tool_error(req_id, str(exc))
            except RuntimeError as exc:
                return _mcp_tool_error(req_id, str(exc))
            except Exception:
                return _mcp_tool_error(req_id, "Internal server error.")
            return _mcp_tool_result(req_id, {"entities": entities, "domain": domain})
        if tool_name != "append_memory":
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


def handler(event: Mapping[str, Any], _context: Any) -> Dict[str, Any]:
    """Lambda entrypoint for MCP and direct append_memory calls."""
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

    # Direct append_memory call fallback.
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
