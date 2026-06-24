"""
Tool-faithful message assembly for the Context Synthesizer proxy.

Compaction replaces *old* transcript with L1/L2, but the active tool loop and
recent turns must pass through with full tool_use / tool_result blocks so
Claude Code reasoning and bash execution stay intact.
"""

from __future__ import annotations

import copy
import json
from typing import Any
TOOL_BLOCK_TYPES = frozenset(
    {
        "tool_use",
        "tool_result",
        "server_tool_use",
        "web_search_tool_result",
        "mcp_tool_use",
        "mcp_tool_result",
    }
)

PASSTHROUGH_BODY_KEYS = (
    "temperature",
    "top_p",
    "top_k",
    "stop_sequences",
    "metadata",
    "system",
    "tools",
    "tool_choice",
    "thinking",
    "service_tier",
    "betas",
    "context_management",
    "mcp_servers",
    "container",
    "output_config",
    "inference_geo",
)

BETA_ONLY_BODY_KEYS = frozenset(
    {
        "betas",
        "mcp_servers",
    }
)

# Claude Code sends native context_management; synthesizer proxy compacts via L1/L2/L3.
PROXY_STRIPPED_BODY_KEYS = frozenset({"context_management"})

_CONTEXT_MGMT_BETA_MARKERS = (
    "context-management",
    "compact-2026",
    "clear-tool-uses",
    "clear-thinking",
)


def filter_betas_for_proxy(betas: Any) -> list[Any] | None:
    """Drop context-management betas — handled by Dreaming v4 instead."""
    if not isinstance(betas, list):
        return None
    kept = [
        b
        for b in betas
        if not any(m in str(b).lower() for m in _CONTEXT_MGMT_BETA_MARKERS)
    ]
    return kept or None


def _iter_content_blocks(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def message_has_tool_blocks(msg: dict[str, Any]) -> bool:
    for block in _iter_content_blocks(msg.get("content")):
        if block.get("type") in TOOL_BLOCK_TYPES:
            return True
    return False


def user_message_has_content(msg: dict[str, Any]) -> bool:
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return len(content) > 0
    return False


def serialize_assistant_content(content: Any) -> Any:
    """Store assistant turns with tool_use blocks intact."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content) if content else ""
    out: list[dict[str, Any]] = []
    for block in content:
        if hasattr(block, "model_dump"):
            out.append(block.model_dump())
        elif isinstance(block, dict):
            out.append(copy.deepcopy(block))
        else:
            text = getattr(block, "text", None)
            if text:
                out.append({"type": "text", "text": text})
    return out


def normalize_content_with_tools(content: Any) -> str:
    """Text extraction for telemetry/compaction; summarizes tool blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                if isinstance(block, str):
                    parts.append(block)
                continue
            btype = block.get("type", "")
            if btype == "text":
                parts.append(block.get("text") or "")
            elif btype == "tool_use":
                name = block.get("name") or "tool"
                parts.append(f"[tool_use: {name}]")
            elif btype == "tool_result":
                parts.append("[tool_result]")
            elif btype in TOOL_BLOCK_TYPES:
                parts.append(f"[{btype}]")
            elif "text" in block:
                parts.append(str(block["text"]))
        return "\n".join(p for p in parts if p)
    if content is None:
        return ""
    return str(content)


def message_char_estimate(msg: dict[str, Any]) -> int:
    content = msg.get("content")
    if isinstance(content, list):
        try:
            return len(json.dumps(content, ensure_ascii=False))
        except TypeError:
            return len(normalize_content_with_tools(content))
    return len(normalize_content_with_tools(content))


def find_last_user_message(incoming: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest user turn in client history (Claude Code may end with assistant)."""
    for msg in reversed(incoming):
        if msg.get("role") == "user":
            return msg
    return None


def incoming_ends_with_user(incoming: list[dict[str, Any]]) -> bool:
    return bool(incoming) and incoming[-1].get("role") == "user"


def find_faithful_tail_start(incoming: list[dict[str, Any]], max_recent_messages: int) -> int:
    """
    Start index for the verbatim suffix of incoming messages.

    Extends backward through active tool loops, but never shorter than the
    configured recent-message window.
    """
    n = len(incoming)
    if n <= 1:
        return 0

    min_window = max(2, max_recent_messages)
    window_start = max(0, n - min_window)

    start = n - 1
    i = n - 1
    while i > 0:
        cur = incoming[i]
        prev = incoming[i - 1]
        if message_has_tool_blocks(cur) or message_has_tool_blocks(prev):
            start = i - 1
            i -= 1
            continue
        if cur.get("role") == "user" and prev.get("role") == "assistant" and message_has_tool_blocks(prev):
            start = i - 1
            i -= 1
            continue
        break

    return min(start, window_start)


def recent_window_has_tools(incoming: list[dict[str, Any]], max_recent_messages: int) -> bool:
    n = len(incoming)
    start = max(0, n - max(2, max_recent_messages))
    return any(message_has_tool_blocks(m) for m in incoming[start:])


MAX_CACHE_CONTROL_BLOCKS = 4


def strip_cache_control_from_content(content: Any) -> Any:
    if isinstance(content, list):
        out: list[Any] = []
        for block in content:
            if isinstance(block, dict):
                out.append({k: v for k, v in block.items() if k != "cache_control"})
            else:
                out.append(block)
        return out
    return content


def strip_message_cache_control(msg: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(msg)
    if "content" in out:
        out["content"] = strip_cache_control_from_content(out["content"])
    return out


def count_cache_control_blocks(messages: list[dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("cache_control"):
                    total += 1
    return total


def enforce_cache_control_budget(
    messages: list[dict[str, Any]],
    *,
    max_blocks: int = MAX_CACHE_CONTROL_BLOCKS,
    preserve_prefix: int = 0,
) -> list[dict[str, Any]]:
    """
    Anthropic allows max 4 cache_control blocks per request.

    Preserve synthesizer prefix breakpoints; strip cache_control from tail first.
    """
    msgs = [copy.deepcopy(m) for m in messages]
    while count_cache_control_blocks(msgs) > max_blocks:
        stripped = False
        for i in range(len(msgs) - 1, preserve_prefix - 1, -1):
            content = msgs[i].get("content")
            if not isinstance(content, list):
                continue
            new_content: list[Any] = []
            removed = False
            for block in content:
                if isinstance(block, dict) and block.get("cache_control"):
                    block = {k: v for k, v in block.items() if k != "cache_control"}
                    removed = True
                new_content.append(block)
            if removed:
                msgs[i] = {**msgs[i], "content": new_content}
                stripped = True
                break
        if not stripped:
            break
    return msgs


def strip_cache_control_from_system(system: Any) -> Any:
    if isinstance(system, list):
        return strip_cache_control_from_content(system)
    return system


def build_upstream_messages(
    *,
    incoming: list[dict[str, Any]],
    compressed_prefix: list[dict[str, Any]],
    rolling_fallback: list[dict[str, Any]],
    max_recent_messages: int,
) -> list[dict[str, Any]]:
    """
    L1/L2 compressed prefix + faithful recent/tool tail.

    Claude Code may end with assistant (prefill / tool loop). In that case the
    full incoming tail is preserved verbatim through the last message.
    """
    if not incoming:
        return list(compressed_prefix)

    n = len(incoming)
    last_role = incoming[-1].get("role")
    prefix_len = len(compressed_prefix)

    if last_role != "user":
        tail_start = find_faithful_tail_start(incoming, max_recent_messages)
        tail = [strip_message_cache_control(m) for m in incoming[tail_start:]]
        out = list(compressed_prefix) + tail
        return enforce_cache_control_budget(out, preserve_prefix=prefix_len)

    last = strip_message_cache_control(incoming[-1])
    if recent_window_has_tools(incoming, max_recent_messages):
        tail_start = find_faithful_tail_start(incoming, max_recent_messages)
        middle = [strip_message_cache_control(m) for m in incoming[tail_start : n - 1]]
    else:
        middle = [strip_message_cache_control(m) for m in rolling_fallback]

    out = list(compressed_prefix) + middle + [last]
    return enforce_cache_control_budget(out, preserve_prefix=prefix_len)


def passthrough_api_kwargs(
    body: dict[str, Any],
    messages: list[dict[str, Any]],
    *,
    use_beta: bool = False,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": body.get("model"),
        "max_tokens": body.get("max_tokens", 8192),
        "messages": messages,
    }
    for key in PASSTHROUGH_BODY_KEYS:
        if key in PROXY_STRIPPED_BODY_KEYS:
            continue
        if not use_beta and key in BETA_ONLY_BODY_KEYS:
            continue
        if key in body and body[key] is not None:
            kwargs[key] = body[key]
    if "betas" in kwargs:
        filtered = filter_betas_for_proxy(kwargs.get("betas"))
        if filtered:
            kwargs["betas"] = filtered
        else:
            kwargs.pop("betas", None)
    if "system" in kwargs:
        kwargs["system"] = strip_cache_control_from_system(kwargs["system"])
    return kwargs


def resolve_messages_api(upstream: Any, use_beta: bool) -> Any:
    """Route to beta.messages when Claude Code sends ?beta=true / betas in body."""
    if use_beta and getattr(upstream, "beta", None):
        return upstream.beta.messages
    return upstream.messages


def request_uses_beta(request: Any, body: dict[str, Any]) -> bool:
    """Claude Code 2.1+ calls POST /v1/messages?beta=true with beta-only body fields."""
    q = str(getattr(request, "query_params", {}).get("beta", "")).lower()
    if q in ("true", "1", "yes"):
        return True
    if body.get("mcp_servers"):
        return True
    if filter_betas_for_proxy(body.get("betas")):
        return True
    return False


def prepare_incoming_messages(incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Drop trailing assistant stubs Claude CLI appends to history batches.

    Keeps tool_use continuations; removes thinking-only / empty assistant tails that
    are invalid terminal messages for the upstream API.
    """
    trimmed = [copy.deepcopy(m) for m in incoming]
    while len(trimmed) > 1 and trimmed[-1].get("role") == "assistant":
        last = trimmed[-1]
        if message_has_tool_blocks(last):
            break
        content = last.get("content")
        if isinstance(content, str) and content.strip():
            break
        if isinstance(content, list):
            types = {b.get("type") for b in content if isinstance(b, dict)}
            if types - {"thinking", "redacted_thinking"}:
                break
        trimmed.pop()
    return trimmed
