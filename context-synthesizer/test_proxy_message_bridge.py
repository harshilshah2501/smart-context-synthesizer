"""Tests for tool-faithful proxy message assembly."""

from __future__ import annotations

from proxy_message_bridge import (
    build_upstream_messages,
    count_cache_control_blocks,
    enforce_cache_control_budget,
    message_has_tool_blocks,
    passthrough_api_kwargs,
    user_message_has_content,
)


def _prefix() -> list[dict]:
    return [{"role": "user", "content": [{"type": "text", "text": "RULES"}]}]


def test_passthrough_forwards_tools_and_thinking():
    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 8192,
        "tools": [{"name": "bash", "description": "run shell"}],
        "tool_choice": {"type": "auto"},
        "thinking": {"type": "enabled", "budget_tokens": 10000},
        "messages": [],
    }
    kwargs = passthrough_api_kwargs(body, [{"role": "user", "content": "hi"}])
    assert "tools" in kwargs
    assert kwargs["tool_choice"] == {"type": "auto"}
    assert kwargs["thinking"]["budget_tokens"] == 10000


def test_user_message_accepts_tool_result_only():
    msg = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tu_1",
                "content": "ok",
            }
        ],
    }
    assert user_message_has_content(msg)
    assert message_has_tool_blocks(msg)


def test_build_upstream_preserves_tool_tail_from_incoming():
    incoming = [
        {"role": "user", "content": "old question"},
        {"role": "assistant", "content": [{"type": "text", "text": "running"}]},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll run git"},
                {"type": "tool_use", "id": "tu_1", "name": "bash", "input": {"command": "git init"}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "Initialized"},
            ],
        },
    ]
    out = build_upstream_messages(
        incoming=incoming,
        compressed_prefix=_prefix(),
        rolling_fallback=[{"role": "user", "content": "stale"}],
        max_recent_messages=4,
    )
    assert out[0]["content"][0]["text"] == "RULES"
    roles_and_types = []
    for m in out[1:]:
        c = m.get("content")
        if isinstance(c, list):
            roles_and_types.append((m["role"], [b.get("type") for b in c]))
        else:
            roles_and_types.append((m["role"], c))
    assert ("assistant", ["text", "tool_use"]) in roles_and_types
    assert ("user", ["tool_result"]) in roles_and_types
    assert ("user", "stale") not in roles_and_types


def test_build_upstream_assistant_last_passthrough():
    incoming = [
        {"role": "user", "content": "create sample-project-2"},
        {"role": "assistant", "content": [{"type": "text", "text": "I'll set that up"}]},
    ]
    out = build_upstream_messages(
        incoming=incoming,
        compressed_prefix=_prefix(),
        rolling_fallback=[],
        max_recent_messages=4,
    )
    assert out[-1]["role"] == "assistant"
    assert out[-2]["content"] == "create sample-project-2"


def test_passthrough_omits_beta_keys_on_stable_api():
    body = {
        "model": "claude-sonnet-4-6",
        "betas": ["context-management-2025-06-27", "tools-2024-04-04"],
        "context_management": {"edits": []},
        "tools": [{"name": "bash"}],
    }
    stable = passthrough_api_kwargs(body, [], use_beta=False)
    beta = passthrough_api_kwargs(body, [], use_beta=True)
    assert "betas" not in stable
    assert "context_management" not in stable
    assert "tools" in stable
    assert "context_management" not in beta
    assert beta.get("betas") == ["tools-2024-04-04"]


def test_build_upstream_uses_rolling_when_no_tools():
    incoming = [
        {"role": "user", "content": "turn 1"},
        {"role": "assistant", "content": "answer 1"},
        {"role": "user", "content": "turn 2"},
    ]
    rolling = [
        {"role": "user", "content": "turn 1"},
        {"role": "assistant", "content": "answer 1"},
    ]
    out = build_upstream_messages(
        incoming=incoming,
        compressed_prefix=_prefix(),
        rolling_fallback=rolling,
        max_recent_messages=4,
    )
    assert out[-1]["content"] == "turn 2"
    assert out[-2]["content"] == "answer 1"


def test_enforce_cache_control_budget_strips_tail():
    prefix = [
        {"role": "user", "content": [{"type": "text", "text": "L1", "cache_control": {"type": "ephemeral"}}]},
        {"role": "user", "content": [{"type": "text", "text": "L2a", "cache_control": {"type": "ephemeral"}}]},
        {"role": "user", "content": [{"type": "text", "text": "L2b", "cache_control": {"type": "ephemeral"}}]},
    ]
    tail = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "more", "cache_control": {"type": "ephemeral"}},
            ],
        }
    ]
    out = enforce_cache_control_budget(prefix + tail, preserve_prefix=3)
    assert count_cache_control_blocks(out) <= 4
    assert count_cache_control_blocks(out[3:]) == 0


def test_build_upstream_strips_tail_cache_control():
    prefix = [
        {"role": "user", "content": [{"type": "text", "text": "L1", "cache_control": {"type": "ephemeral"}}]},
        {"role": "user", "content": [{"type": "text", "text": "L2a", "cache_control": {"type": "ephemeral"}}]},
        {"role": "user", "content": [{"type": "text", "text": "L2b", "cache_control": {"type": "ephemeral"}}]},
    ]
    incoming = [
        {"role": "user", "content": "old"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "q", "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "extra", "cache_control": {"type": "ephemeral"}},
            ],
        },
    ]
    out = build_upstream_messages(
        incoming=incoming,
        compressed_prefix=prefix,
        rolling_fallback=[],
        max_recent_messages=4,
    )
    assert count_cache_control_blocks(out) <= 4
