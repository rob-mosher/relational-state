from __future__ import annotations

import importlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

mcp_server = importlib.import_module("infra.lambda.mcp_server.handler")


@pytest.fixture(autouse=True)
def clear_bucket_env() -> None:
    os.environ.pop(mcp_server.MEMORY_BUCKET_ENV, None)
    os.environ.pop(mcp_server.OAUTH_ISSUER_ENV, None)
    os.environ.pop(mcp_server.OAUTH_AUTHORIZATION_ENDPOINT_ENV, None)
    os.environ.pop(mcp_server.OAUTH_TOKEN_ENDPOINT_ENV, None)
    os.environ.pop(mcp_server.OAUTH_USERINFO_ENDPOINT_ENV, None)
    os.environ.pop(mcp_server.OAUTH_JWKS_URI_ENV, None)
    os.environ.pop(mcp_server.OAUTH_REGISTRATION_ENDPOINT_ENV, None)
    os.environ.pop(mcp_server.OAUTH_RESOURCE_ENV, None)
    os.environ.pop(mcp_server.OAUTH_SCOPES_ENV, None)
    os.environ.pop(mcp_server.OAUTH_ALLOWED_REDIRECT_URI_EXACT_ENV, None)
    os.environ.pop(mcp_server.OAUTH_ALLOWED_REDIRECT_URI_PREFIX_ENV, None)
    os.environ.pop(mcp_server.ENABLE_DCR_PROXY_ENV, None)
    os.environ.pop(mcp_server.COGNITO_USER_POOL_ID_ENV, None)


def test_prepare_memory_record_builds_expected_shape() -> None:
    body: Dict[str, Any] = {
        "entity_id": "rob",
        "topic": "work",
        "content": "Met with the platform team.",
        "timestamp": "2026-01-27T03:14:22-05:00",
        "metadata": {"tags": ["meeting"]},
    }

    record = mcp_server._prepare_memory_record(body)

    assert record.payload["schema_version"] == 1
    assert record.payload["entity_id"] == "rob"
    assert record.payload["topic"] == "work"
    assert record.payload["content"] == "Met with the platform team."
    assert record.payload["metadata"] == {
        "tags": ["meeting"],
        "client_timestamp": "2026-01-27T03:14:22-05:00",
    }

    # Timestamp is server-assigned (UTC, seconds precision).
    assert record.payload["timestamp"].endswith("Z")
    parsed = datetime.strptime(
        record.payload["timestamp"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=UTC)
    delta = datetime.now(tz=UTC) - parsed
    assert abs(delta.total_seconds()) < 5

    assert record.s3_key.startswith("memories/topic=work/entity=rob/")
    assert record.s3_key.endswith(f"_{record.memory_id}.json")


def test_normalize_timestamp_defaults_to_now_utc() -> None:
    ts = mcp_server._normalize_timestamp(None)
    assert ts.endswith("Z")
    parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    # Ensure it parses and is close to now.
    delta = datetime.now(tz=UTC) - parsed
    assert abs(delta.total_seconds()) < 5


@pytest.mark.parametrize(
    "field,value",
    [
        ("entity_id", ""),
        ("topic", ""),
        ("content", ""),
    ],
)
def test_required_fields_must_be_non_empty(field: str, value: str) -> None:
    body: Dict[str, Any] = {
        "entity_id": "rob",
        "topic": "work",
        "content": "note",
    }
    body[field] = value

    with pytest.raises(mcp_server.RequestError):
        mcp_server._prepare_memory_record(body)


def test_handler_success_returns_ok_after_s3_write(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"
    captured: Dict[str, Any] = {}

    def fake_put_object_s3(*, bucket: str, key: str, payload: Dict[str, Any]) -> None:
        captured["bucket"] = bucket
        captured["key"] = key
        captured["payload"] = payload

    monkeypatch.setattr(mcp_server, "_put_object_s3", fake_put_object_s3)

    response = mcp_server.handler(
        {
            "entity_id": "rob",
            "topic": "work",
            "content": "Ship the ingress.",
        },
        None,
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"
    assert body["memory_id"] == captured["payload"]["memory_id"]
    assert body["s3_key"] == captured["key"]
    assert captured["bucket"] == "memory-bucket"


def test_mcp_initialize_returns_server_info() -> None:
    response = mcp_server.handler(
        {"body": json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})},
        None,
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["result"]["serverInfo"]["name"] == mcp_server.SERVER_NAME


@pytest.mark.parametrize(
    "method,expected_key",
    [
        ("resources/list", "resources"),
        ("resource_templates/list", "resourceTemplates"),
        ("prompts/list", "prompts"),
    ],
)
def test_mcp_optional_lists_return_empty(method: str, expected_key: str) -> None:
    response = mcp_server.handler(
        {"body": json.dumps({"jsonrpc": "2.0", "id": 2, "method": method})},
        None,
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["result"][expected_key] == []


def test_mcp_tools_call_adds_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"
    monkeypatch.setattr(mcp_server, "_put_object_s3", lambda **_: None)

    payload = {
        "jsonrpc": "2.0",
        "id": "abc",
        "method": "tools/call",
        "params": {
            "name": "add_memory",
            "arguments": {
                "entity_id": "rob",
                "topic": "work",
                "content": "MCP write",
            },
        },
    }

    response = mcp_server.handler({"body": json.dumps(payload)}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["result"]["content"][0]["type"] == "text"


def test_mcp_tools_list_includes_get_readme() -> None:
    response = mcp_server.handler(
        {"body": json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})},
        None,
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    tool_names = {tool["name"] for tool in body["result"]["tools"]}
    assert "get_README" in tool_names
    assert "list_topics" in tool_names
    assert "list_entities_within_topic" in tool_names
    assert "add_memory" in tool_names


def test_mcp_tools_call_get_readme_returns_text() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": "readme",
        "method": "tools/call",
        "params": {"name": "get_README", "arguments": {}},
    }

    response = mcp_server.handler({"body": json.dumps(payload)}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    content_text = body["result"]["content"][0]["text"]
    payload_text = json.loads(content_text)["readme"]
    assert "Relational State" in payload_text
    assert "Current state" in payload_text


def test_mcp_tools_call_list_topics_returns_topics(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"
    monkeypatch.setattr(mcp_server, "_list_topics_s3", lambda **_: ["alpha", "beta"])

    payload = {
        "jsonrpc": "2.0",
        "id": "topics",
        "method": "tools/call",
        "params": {"name": "list_topics", "arguments": {}},
    }

    response = mcp_server.handler({"body": json.dumps(payload)}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    content_text = body["result"]["content"][0]["text"]
    payload_text = json.loads(content_text)
    assert payload_text["topics"] == ["alpha", "beta"]


def test_mcp_tools_call_list_entities_within_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"
    monkeypatch.setattr(mcp_server, "_list_entities_s3", lambda **_: ["alice", "rob"])

    payload = {
        "jsonrpc": "2.0",
        "id": "entities",
        "method": "tools/call",
        "params": {"name": "list_entities_within_topic", "arguments": {"topic": "work"}},
    }

    response = mcp_server.handler({"body": json.dumps(payload)}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    content_text = body["result"]["content"][0]["text"]
    payload_text = json.loads(content_text)
    assert payload_text["topic"] == "work"
    assert payload_text["entities"] == ["alice", "rob"]


def test_mcp_tools_call_list_entities_with_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"
    monkeypatch.setattr(mcp_server, "_list_entities_s3", lambda **_: ["chatgpt-codex-5.2"])

    payload = {
        "jsonrpc": "2.0",
        "id": "entities-prefix",
        "method": "tools/call",
        "params": {
            "name": "list_entities_within_topic",
            "arguments": {"topic": "test", "entity_prefix": "chatgpt"},
        },
    }

    response = mcp_server.handler({"body": json.dumps(payload)}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    content_text = body["result"]["content"][0]["text"]
    payload_text = json.loads(content_text)
    assert payload_text["topic"] == "test"
    assert payload_text["entity_prefix"] == "chatgpt"
    assert payload_text["entities"] == ["chatgpt-codex-5.2"]


def test_tools_call_accepts_stringified_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"
    monkeypatch.setattr(mcp_server, "_put_object_s3", lambda **_: None)

    args = json.dumps(
        {
            "entity_id": "rob",
            "topic": "work",
            "content": "Stringified args.",
        }
    )
    payload = {
        "jsonrpc": "2.0",
        "id": "string-args",
        "method": "tools/call",
        "params": {"name": "add_memory", "arguments": args},
    }

    response = mcp_server.handler({"body": json.dumps(payload)}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["result"]["content"][0]["type"] == "text"


def test_handler_returns_error_when_s3_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ[mcp_server.MEMORY_BUCKET_ENV] = "memory-bucket"

    def failing_put_object_s3(**_: Any) -> None:
        raise RuntimeError("Failed to write memory to S3.")

    monkeypatch.setattr(mcp_server, "_put_object_s3", failing_put_object_s3)

    response = mcp_server.handler(
        {
            "entity_id": "rob",
            "topic": "work",
            "content": "This should fail.",
        },
        None,
    )

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body == {"status": "error", "error": "Failed to write memory to S3."}


def test_oauth_protected_resource_route_from_raw_path() -> None:
    os.environ[mcp_server.OAUTH_ISSUER_ENV] = "https://issuer.example.com"
    os.environ[mcp_server.OAUTH_RESOURCE_ENV] = "https://mcp.example.com/"
    os.environ[mcp_server.OAUTH_JWKS_URI_ENV] = "https://issuer.example.com/jwks"
    os.environ[mcp_server.OAUTH_SCOPES_ENV] = "openid profile"

    event = {
        "rawPath": "/.well-known/oauth-protected-resource",
        "requestContext": {"http": {"method": "GET"}, "stage": "dev"},
    }

    response = mcp_server.handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["resource"] == "https://mcp.example.com/"
    assert body["authorization_servers"] == ["https://issuer.example.com"]
    assert body["scopes_supported"] == ["openid", "profile"]


def test_oauth_authorization_server_route_with_stage_prefixed_path() -> None:
    os.environ[mcp_server.OAUTH_ISSUER_ENV] = "https://issuer.example.com"
    os.environ[mcp_server.OAUTH_AUTHORIZATION_ENDPOINT_ENV] = (
        "https://issuer.example.com/oauth2/authorize"
    )
    os.environ[mcp_server.OAUTH_TOKEN_ENDPOINT_ENV] = (
        "https://issuer.example.com/oauth2/token"
    )

    event = {
        "requestContext": {
            "http": {"method": "GET", "path": "/dev/.well-known/oauth-authorization-server"},
            "stage": "dev",
        },
    }

    response = mcp_server.handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["issuer"] == "https://issuer.example.com"
    assert body["authorization_endpoint"] == "https://issuer.example.com/oauth2/authorize"
    assert body["token_endpoint"] == "https://issuer.example.com/oauth2/token"
