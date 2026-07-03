"""Tests for tool-faithful proxy message assembly."""

from __future__ import annotations

from proxy_message_bridge import (
    align_tail_start_for_tool_chain,
    build_upstream_messages,
    count_cache_control_blocks,
    enforce_cache_control_budget,
    message_has_tool_blocks,
    normalize_content_with_tools,
    passthrough_api_kwargs,
    repair_orphaned_tool_results,
    user_message_has_content,
)
from compaction import prepare_turn_text


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


def test_passthrough_sanitizes_model_name_from_ansi_noise():
    body = {
        "model": "claude-opus-4-8[1m",
        "max_tokens": 8192,
    }
    kwargs = passthrough_api_kwargs(body, [{"role": "user", "content": "hi"}])
    assert kwargs["model"] == "claude-opus-4-8"


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


def test_normalize_content_keeps_tool_result_payload_text():
    content = [
        {"type": "text", "text": "checking deps"},
        {
            "type": "tool_result",
            "tool_use_id": "tu_1",
            "content": [
                {"type": "text", "text": "package.json => react 19.0.0"},
                {"type": "text", "text": "vite 6.1.0"},
            ],
        },
    ]
    out = normalize_content_with_tools(content)
    assert "[tool_result]" in out
    assert "react 19.0.0" in out


def test_prepare_turn_text_keeps_different_updates_same_path():
    raw = "\n".join(
        [
            "/repo/api/client.py: uses requests",
            "/repo/api/client.py: updated retry policy after regression",
        ]
    )
    out = prepare_turn_text(raw)
    assert out.count("/repo/api/client.py") == 2


def test_align_tail_start_includes_assistant_before_tool_result():
    incoming = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": [{"type": "text", "text": "read file"}]},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "tu_read", "name": "Read", "input": {"path": "Foo.java"}},
            ],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "tu_read", "content": "class Foo {}"}],
        },
    ]
    # Slice from tool_result alone would omit the assistant at index 2
    assert align_tail_start_for_tool_chain(incoming, 3) == 2


def test_build_upstream_tool_result_not_first_after_prefix():
    """Regression: prefix is all user-role; tail must not start with orphan tool_result."""
    incoming = [
        {"role": "user", "content": "msg " + str(i)} for i in range(30)
    ]
    incoming.extend(
        [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "tu_1", "name": "Read", "input": {"path": "Config.java"}},
                ],
            },
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "tu_1", "content": "ok"}],
            },
        ]
    )
    prefix = [
        {"role": "user", "content": [{"type": "text", "text": "L1"}]},
        {"role": "user", "content": [{"type": "text", "text": "L2"}]},
    ]
    out = build_upstream_messages(
        incoming=incoming,
        compressed_prefix=prefix,
        rolling_fallback=[{"role": "user", "content": "stale"}],
        max_recent_messages=4,
    )
    assert out[0]["content"][0]["text"] == "L1"
    assert out[1]["content"][0]["text"] == "L2"
    first_tail = out[2]
    if isinstance(first_tail.get("content"), list):
        block_types = [b.get("type") for b in first_tail["content"] if isinstance(b, dict)]
        assert "tool_result" not in block_types
    assert out[-2]["role"] == "assistant"
    assert out[-2]["content"][0]["type"] == "tool_use"
    assert out[-1]["content"][0]["type"] == "tool_result"


def test_repair_orphaned_tool_results_strips_unpaired():
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "rules"}]},
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "tu_orphan", "content": "bad"}],
        },
        {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "tu_ok", "name": "bash", "input": {}}],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "tu_ok", "content": "ok"}],
        },
    ]
    out = repair_orphaned_tool_results(messages)
    assert len(out) == 3
    assert out[0]["content"][0]["text"] == "rules"
    assert out[1]["content"][0]["type"] == "tool_use"
    assert out[2]["content"][0]["tool_use_id"] == "tu_ok"


def test_build_upstream_assistant_last_includes_tool_use_before_result():
    incoming = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "tu_1", "name": "Read", "input": {"path": "Config.java"}},
            ],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "tu_1", "content": "class Config {}"}],
        },
    ]
    prefix = [{"role": "user", "content": [{"type": "text", "text": "RULES"}]}]
    out = build_upstream_messages(
        incoming=incoming,
        compressed_prefix=prefix,
        rolling_fallback=[],
        max_recent_messages=4,
    )
    assert out[1]["role"] == "assistant"
    assert out[1]["content"][0]["type"] == "tool_use"
    assert out[2]["content"][0]["type"] == "tool_result"
