"""FastAPI contract tests for proxy and dashboard routes."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "context-synthesizer"


def test_list_models(client):
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"
    assert len(data["data"]) >= 1
    assert "claude" in data["data"][0]["id"]


def test_messages_rejects_missing_api_key(client):
    res = client.post(
        "/v1/messages",
        headers={"X-Session-Id": "contract-test"},
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert res.status_code == 401


def test_chat_completions_rejects_missing_api_key(client):
    res = client.post(
        "/v1/chat/completions",
        headers={"X-Session-Id": "contract-test"},
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert res.status_code == 401


def test_messages_rejects_empty_body(client):
    res = client.post(
        "/v1/messages",
        headers={"x-api-key": "sk-test-key"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 64, "messages": []},
    )
    assert res.status_code == 400


@patch("proxy_tool.upstream_messages_create", new_callable=AsyncMock)
def test_messages_forwards_with_api_key(mock_upstream, client):
    block = SimpleNamespace(text="pong")
    mock_upstream.return_value = SimpleNamespace(
        content=[block],
        usage=SimpleNamespace(
            input_tokens=10,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            output_tokens=5,
        ),
        model_dump=lambda: {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "pong"}],
            "model": "claude-sonnet-4-6",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    )

    res = client.post(
        "/v1/messages",
        headers={"x-api-key": "sk-test-key", "X-Session-Id": "contract-test"},
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "ping"}],
        },
    )
    assert res.status_code == 200
    assert res.json()["content"][0]["text"] == "pong"
    mock_upstream.assert_awaited_once()


def test_dashboard_data_open_without_token(client):
    res = client.get("/api/dashboard/data")
    assert res.status_code == 200
    body = res.json()
    assert "summary" in body
    assert "prefix_cache" in body


def test_dashboard_requires_token_when_configured(client, monkeypatch):
    monkeypatch.setattr("dashboard_auth.dashboard_token", lambda: "secret-token")
    res = client.get("/api/dashboard/data")
    assert res.status_code == 401
    res = client.get("/api/dashboard/data?token=secret-token")
    assert res.status_code == 200


def test_dashboard_localhost_only_blocks_testclient(client, monkeypatch):
    monkeypatch.setattr("dashboard_auth.dashboard_localhost_only", lambda: True)
    res = client.get("/api/dashboard/data")
    assert res.status_code == 403


def test_dashboard_meta(client):
    res = client.get("/api/dashboard/meta")
    assert res.status_code == 200
    body = res.json()
    assert body["endpoints"]["data"] == "/api/dashboard/data"
