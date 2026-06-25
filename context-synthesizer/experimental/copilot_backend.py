"""
EXPERIMENTAL — NOT LOADED BY THE PROXY.

GitHub Copilot backend shim (archived). See experimental/README.md.
Routing Claude traffic through Copilot may violate GitHub ToS.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from proxy_message_bridge import normalize_content_with_tools

COPILOT_BASE_URL: str = "https://api.githubcopilot.com"


def _to_copilot_model(model: str) -> str:
    m = re.sub(r"-\d{8}$", "", model)
    m = re.sub(r"-(\d+)$", r".\1", m)
    return m


def _strip_cache_control(content: Any) -> Any:
    if isinstance(content, list):
        return [
            {k: v for k, v in block.items() if k != "cache_control"}
            for block in content
            if isinstance(block, dict)
        ]
    return content


def _anthropic_msgs_to_oai(
    messages: list[dict[str, Any]],
    system: str | None = None,
) -> list[dict[str, Any]]:
    oai: list[dict[str, Any]] = []
    if system:
        oai.append({"role": "system", "content": system})
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = _strip_cache_control(content)
        text = normalize_content_with_tools(content)
        oai.append({"role": role, "content": text})
    return oai


def _anthropic_kwargs_to_oai(api_kwargs: dict[str, Any]) -> dict[str, Any]:
    model = _to_copilot_model(api_kwargs.get("model", "claude-sonnet-4.6"))
    system = api_kwargs.get("system")
    oai_messages = _anthropic_msgs_to_oai(api_kwargs.get("messages", []), system=system)
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": api_kwargs.get("max_tokens", 8192),
        "messages": oai_messages,
    }
    for key in ("temperature", "top_p"):
        if key in api_kwargs and api_kwargs[key] is not None:
            body[key] = api_kwargs[key]
    return body


@dataclass
class _CopilotUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    @classmethod
    def from_oai(cls, usage: dict[str, Any]) -> "_CopilotUsage":
        return cls(
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )


class _CopilotContentBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text

    def model_dump(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text}


class _CopilotResponse:
    def __init__(self, text: str, model: str, usage: "_CopilotUsage") -> None:
        self.content = [_CopilotContentBlock(text)]
        self.model = model
        self.stop_reason = "end_turn"
        self.usage = usage

    def model_dump(self) -> dict[str, Any]:
        return {
            "id": f"msg_copilot_{int(time.time() * 1000)}",
            "type": "message",
            "role": "assistant",
            "content": [b.model_dump() for b in self.content],
            "model": self.model,
            "stop_reason": self.stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        }


class _SyntheticEvent:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _CopilotStreamCtx:
    def __init__(self, token: str, base_url: str, api_kwargs: dict[str, Any]) -> None:
        self._token = token
        self._base_url = base_url
        self._oai_body = _anthropic_kwargs_to_oai(api_kwargs)
        self._model = self._oai_body.get("model", "")
        self._text = ""
        self._usage: _CopilotUsage = _CopilotUsage()

    async def __aenter__(self) -> "_CopilotStreamCtx":
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=self._oai_body,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                    "Copilot-Integration-Id": "vscode-chat",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        self._text = (choice.get("message") or {}).get("content") or ""
        self._usage = _CopilotUsage.from_oai(data.get("usage") or {})
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def __aiter__(self):
        return self._iter_events()

    async def _iter_events(self):
        yield _SyntheticEvent({
            "type": "message_start",
            "message": {
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": self._model,
                "stop_reason": None,
                "usage": {"input_tokens": self._usage.input_tokens, "output_tokens": 0},
            },
        })
        yield _SyntheticEvent({
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        })
        if self._text:
            yield _SyntheticEvent({
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": self._text},
            })
        yield _SyntheticEvent({"type": "content_block_stop", "index": 0})
        yield _SyntheticEvent({
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": self._usage.output_tokens},
        })
        yield _SyntheticEvent({"type": "message_stop"})

    @property
    def text_stream(self):
        return self._text_gen()

    async def _text_gen(self):
        if self._text:
            yield self._text

    async def get_final_message(self) -> _CopilotResponse:
        return _CopilotResponse(self._text, self._model, self._usage)


class _CopilotMessages:
    def __init__(self, token: str, base_url: str) -> None:
        self._token = token
        self._base_url = base_url

    async def create(self, **kwargs: Any) -> _CopilotResponse:
        oai_body = _anthropic_kwargs_to_oai(kwargs)
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=oai_body,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                    "Copilot-Integration-Id": "vscode-chat",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        usage = _CopilotUsage.from_oai(data.get("usage") or {})
        return _CopilotResponse(text, oai_body.get("model", ""), usage)

    def stream(self, **kwargs: Any) -> _CopilotStreamCtx:
        return _CopilotStreamCtx(self._token, self._base_url, kwargs)


class CopilotBackend:
    """Drop-in replacement for AsyncAnthropic when using Copilot (unsupported)."""

    def __init__(self, token: str, base_url: str = "") -> None:
        self.messages = _CopilotMessages(token, base_url or COPILOT_BASE_URL)
