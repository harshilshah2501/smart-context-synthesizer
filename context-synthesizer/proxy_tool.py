"""
Local API gateway proxy for Claude Code → Anthropic with index-aligned prompt caching
and pinned checkpoint memory (L2a).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

import uvicorn
from anthropic import AsyncAnthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from dashboard_routes import attach_dashboard
from compaction import build_compaction_prompt, extract_pins, format_turns_for_compaction
from models import DEFAULT_CHAT_MODEL, DEFAULT_COMPACTION_MODEL
from telemetry import (
    ContextSnapshot,
    MIN_CACHE_TOKENS,
    UsageSnapshot,
    append_event,
    compute_costs,
    compute_synthesis_metrics,
    estimate_tokens,
    print_telemetry_report,
    TelemetryEvent,
    utc_now_iso,
)

def _check_claude_settings() -> None:
    """Warn at startup if Claude Code isn't wired to this proxy."""
    port = os.environ.get("PROXY_PORT", "8080")
    settings_path = Path(
        os.environ.get("CLAUDE_SETTINGS_PATH", str(Path.home() / ".claude" / "settings.json"))
    )

    def _read_base_url(path: Path) -> str:
        if not path.is_file():
            return ""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return (data.get("env") or {}).get("ANTHROPIC_BASE_URL") or ""
        except Exception:
            return ""

    base_url = _read_base_url(settings_path)
    if not base_url:
        print(
            f"[PROXY] ⚠ ANTHROPIC_BASE_URL not set in {settings_path}\n"
            f"  Run: bash context-synthesizer/scripts/configure_claude_proxy.sh\n"
            f"  Expected: http://127.0.0.1:{port}",
            file=sys.stderr,
            flush=True,
        )
    elif f":{port}" not in base_url and "127.0.0.1" not in base_url and "localhost" not in base_url:
        print(
            f"[PROXY] ⚠ ANTHROPIC_BASE_URL in {settings_path} is '{base_url}' — "
            f"does not point at this proxy (expected http://127.0.0.1:{port}).",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(f"[PROXY] Claude Code (WSL) → proxy: {base_url}", flush=True)

    # WSL: Windows Claude Code app needs WSL IP, not 127.0.0.1
    wsl_marker = Path("/proc/version")
    if wsl_marker.is_file() and "microsoft" in wsl_marker.read_text(encoding="utf-8", errors="ignore").lower():
        win_settings = os.environ.get("CLAUDE_WINDOWS_SETTINGS_PATH", "")
        if not win_settings:
            for mount in Path("/mnt/c/Users").iterdir() if Path("/mnt/c/Users").is_dir() else []:
                candidate = mount / ".claude" / "settings.json"
                if candidate.is_file():
                    win_settings = str(candidate)
                    break
        if win_settings:
            win_url = _read_base_url(Path(win_settings))
            if win_url and "127.0.0.1" in win_url and f":{port}" in win_url:
                print(
                    f"[PROXY] ⚠ Windows Claude settings ({win_settings}) use 127.0.0.1 — "
                    "Windows localhost is NOT the WSL proxy.\n"
                    "  Run: bash context-synthesizer/scripts/configure_claude_proxy.sh\n"
                    "  Then restart Claude Code on Windows.",
                    file=sys.stderr,
                    flush=True,
                )
            elif win_url:
                print(f"[PROXY] Claude Code (Windows) → proxy: {win_url}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CLAUDE_MD_CONTENT
    CLAUDE_MD_CONTENT = load_claude_md()
    from dashboard_auth import dashboard_localhost_only, dashboard_token
    from telemetry import TELEMETRY_LOG_PATH

    l1_est = estimate_tokens(len(CLAUDE_MD_CONTENT))
    print(
        f"[PROXY] Loaded Claude.md from {CLAUDE_MD_PATH} "
        f"({len(CLAUDE_MD_CONTENT):,} chars, ~{l1_est:,} tok est.)",
        flush=True,
    )
    if l1_est < MIN_CACHE_TOKENS:
        print(
            f"[PROXY] ⚠ Layer 1 below {MIN_CACHE_TOKENS:,} token cache minimum. "
            "Run build_production_claude_md.py and set CLAUDE_MD_PATH.",
            flush=True,
        )
    print(f"[PROXY] Chat model: {DEFAULT_MODEL} | Compaction model: {COMPACTION_MODEL}", flush=True)
    print(
        f"[PROXY] Compaction: every {MAX_TURNS_THRESHOLD} turns | "
        f"Layer3 cap {MAX_LAYER3_TURNS} turns | "
        f"token threshold {COMPACTION_TOKEN_THRESHOLD:,} (0=off)",
        flush=True,
    )
    print(f"[PROXY] Checkpoints: max {MAX_CHECKPOINTS} pins per session (@synth-remember:)", flush=True)
    print(f"[PROXY] Telemetry log: {TELEMETRY_LOG_PATH}", flush=True)
    print("[PROXY] Auth: Claude CLI BYOK (x-api-key per request) or ANTHROPIC_API_KEY env fallback", flush=True)
    host = os.environ.get("PROXY_HOST", "127.0.0.1")
    port = os.environ.get("PROXY_PORT", "8080")
    dash_url = f"http://{host}:{port}/dashboard"
    if dashboard_token():
        dash_url += "?token=<DASHBOARD_TOKEN>"
    print(f"[PROXY] Live dashboard: {dash_url}", flush=True)
    if host == "0.0.0.0" and not dashboard_token() and not dashboard_localhost_only():
        print(
            "[PROXY] ⚠ PROXY_HOST=0.0.0.0 without DASHBOARD_TOKEN — "
            "dashboard is reachable on your LAN. Set DASHBOARD_TOKEN in .env or re-run setup.",
            flush=True,
        )
    if dashboard_localhost_only():
        print("[PROXY] Dashboard: localhost-only (DASHBOARD_LOCALHOST_ONLY=1)", flush=True)
    elif dashboard_token():
        print("[PROXY] Dashboard: token required (DASHBOARD_TOKEN set)", flush=True)
    log_mode = os.environ.get("PROXY_ACCESS_LOG", "api")
    print(f"[PROXY] Access log: {log_mode} (set PROXY_ACCESS_LOG=all for full trace)", flush=True)
    _check_claude_settings()
    yield
    # no cleanup needed


app = FastAPI(title="Context Synthesizer Proxy", lifespan=lifespan)
attach_dashboard(app)


def _access_log_enabled() -> bool:
    return os.environ.get("PROXY_ACCESS_LOG", "api").strip().lower() not in ("0", "false", "off")


def _access_log_worthy(method: str, path: str, status: int) -> bool:
    mode = os.environ.get("PROXY_ACCESS_LOG", "api").strip().lower()
    if mode in ("0", "false", "off"):
        return False
    if mode == "all":
        return True
    # "api" — log API traffic and errors; skip dashboard/health polling noise
    if path.startswith("/v1/"):
        return True
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    if status >= 400:
        return True
    return False


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "?"


def _ua_short(request: Request, limit: int = 80) -> str:
    ua = (request.headers.get("user-agent") or "-").replace("\n", " ")
    return ua[:limit] + ("…" if len(ua) > limit else "")


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    if not _access_log_enabled():
        return await call_next(request)
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    path = request.url.path
    method = request.method
    status = response.status_code
    if _access_log_worthy(method, path, status):
        print(
            f"[ACCESS] {method} {path} {status} {elapsed_ms:.0f}ms "
            f"client={_client_ip(request)} ua={_ua_short(request)}",
            flush=True,
        )
    return response

DEFAULT_CLAUDE_MD_PATH = Path(__file__).resolve().parent / "Claude.md"
CLAUDE_MD_PATH = Path(os.environ.get("CLAUDE_MD_PATH", str(DEFAULT_CLAUDE_MD_PATH)))
MAX_TURNS_THRESHOLD = int(os.environ.get("MAX_TURNS_THRESHOLD", "10"))
MAX_LAYER3_TURNS = int(os.environ.get("MAX_LAYER3_TURNS", str(MAX_TURNS_THRESHOLD)))
COMPACTION_TOKEN_THRESHOLD = int(os.environ.get("COMPACTION_TOKEN_THRESHOLD", "100000"))
MAX_CHECKPOINTS = int(os.environ.get("MAX_CHECKPOINTS", "20"))
DEFAULT_MODEL = DEFAULT_CHAT_MODEL
COMPACTION_MODEL = DEFAULT_COMPACTION_MODEL
LEDGER_PREFIX = "Current Architectural State:\n"
CHECKPOINTS_PREFIX = (
    "Pinned Checkpoints — always preserved across compactions "
    "(bug fixes, migrations, key decisions):\n"
)

CLAUDE_MD_CONTENT: str = ""
DEFAULT_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip() or None

# ── GitHub Copilot backend ────────────────────────────────────────────────────
# Set COPILOT_TOKEN (GitHub OAuth token from `gh auth token`) to route all LLM
# traffic through api.githubcopilot.com instead of api.anthropic.com.
# The Anthropic SDK is bypassed; requests are translated to OpenAI format.
COPILOT_TOKEN: str | None = os.environ.get("COPILOT_TOKEN", "").strip() or None
COPILOT_BASE_URL: str = os.environ.get("COPILOT_BASE_URL", "https://api.githubcopilot.com")


def _to_copilot_model(model: str) -> str:
    """Translate Anthropic dash-notation model IDs to Copilot dot-notation."""
    m = re.sub(r"-\d{8}$", "", model)       # strip date suffix e.g. -20251001
    m = re.sub(r"-(\d+)$", r".\1", m)        # last -N → .N  e.g. -6 → .6
    return m


def _strip_cache_control(content: Any) -> Any:
    """Remove cache_control fields that the Copilot API rejects."""
    if isinstance(content, list):
        return [{k: v for k, v in block.items() if k != "cache_control"}
                for block in content if isinstance(block, dict)]
    return content


def _anthropic_msgs_to_oai(messages: list[dict[str, Any]],
                            system: str | None = None) -> list[dict[str, Any]]:
    """Convert Anthropic-format messages list to OpenAI format."""
    oai: list[dict[str, Any]] = []
    if system:
        oai.append({"role": "system", "content": system})
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = _strip_cache_control(content)
        text = normalize_content(content)
        oai.append({"role": role, "content": text})
    return oai


def _anthropic_kwargs_to_oai(api_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Convert Anthropic messages.create() kwargs to OpenAI chat/completions body."""
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
    """Anthropic-compatible response object wrapping a Copilot API reply."""

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
    """Minimal Anthropic SSE event wrapper that satisfies proxy_tool's model_dump() calls."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _CopilotStreamCtx:
    """
    Async context manager that mimics AsyncAnthropic.messages.stream().

    Pre-fetches the full Copilot response in __aenter__, then serves both
    text_stream (for OAI streaming path) and __aiter__ synthetic Anthropic
    events (for Anthropic streaming path) from the buffered result.
    """

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
        """Yield synthetic Anthropic-format SSE events from the pre-fetched response."""
        yield _SyntheticEvent({
            "type": "message_start",
            "message": {
                "type": "message", "role": "assistant", "content": [],
                "model": self._model, "stop_reason": None,
                "usage": {"input_tokens": self._usage.input_tokens, "output_tokens": 0},
            },
        })
        yield _SyntheticEvent({"type": "content_block_start", "index": 0,
                               "content_block": {"type": "text", "text": ""}})
        if self._text:
            yield _SyntheticEvent({
                "type": "content_block_delta", "index": 0,
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
    """Drop-in replacement for AsyncAnthropic when COPILOT_TOKEN is set."""

    def __init__(self, token: str, base_url: str = "") -> None:
        self.messages = _CopilotMessages(token, base_url or COPILOT_BASE_URL)


_sessions: dict[str, "SessionState"] = {}
_sessions_lock = asyncio.Lock()


@dataclass
class Checkpoint:
    """A developer-pinned fact that must survive every compaction cycle."""
    text: str
    turn: int   # lifetime turn number when pinned
    ts: str     # ISO timestamp


@dataclass
class SessionState:
    history_ledger: str = "Initial State: System active and optimized."
    rolling_recent_turns: list[dict[str, Any]] = field(default_factory=list)
    pinned_checkpoints: list[Checkpoint] = field(default_factory=list)
    turn_counter: int = 0
    lifetime_turns: int = 0
    api_key: str | None = None
    compaction_in_flight: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def resolve_api_key(request: Request) -> str | None:
    """Claude CLI forwards the developer's key as x-api-key when using ANTHROPIC_BASE_URL."""
    header_key = request.headers.get("x-api-key")
    if header_key and header_key.strip():
        return header_key.strip()
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return token
    return DEFAULT_API_KEY


def anthropic_client(api_key: str) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=api_key)


def build_upstream(api_key: str | None) -> "AsyncAnthropic | CopilotBackend":
    """Return a Copilot backend when COPILOT_TOKEN is set, otherwise Anthropic."""
    if COPILOT_TOKEN:
        return CopilotBackend(COPILOT_TOKEN)
    if not api_key:
        raise ValueError("No API key available for upstream LLM call")
    return AsyncAnthropic(api_key=api_key)


def load_claude_md(path: Path = CLAUDE_MD_PATH) -> str:
    if not path.is_file():
        raise FileNotFoundError(
            f"Claude.md not found at {path}. Set CLAUDE_MD_PATH or create the file."
        )
    return path.read_text(encoding="utf-8")


def normalize_content(content: Any) -> str:
    """JetBrains may send plain strings or Anthropic-style content block arrays."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text") or "")
                elif "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    if content is None:
        return ""
    return str(content)


def extract_assistant_text(content_blocks: Any) -> str:
    if not content_blocks:
        return ""
    parts: list[str] = []
    for block in content_blocks:
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if text:
            parts.append(text)
    return "".join(parts)


async def get_session(session_id: str) -> SessionState:
    async with _sessions_lock:
        if session_id not in _sessions:
            _sessions[session_id] = SessionState()
        return _sessions[session_id]


def build_layer1_message() -> dict[str, Any]:
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": CLAUDE_MD_CONTENT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
    }


def build_layer2a_message(checkpoints: list[Checkpoint]) -> dict[str, Any]:
    """L2a — pinned checkpoints block, cached, append-only, never summarised away."""
    bullets = "\n".join(f"- [T{c.turn}] {c.text}" for c in checkpoints)
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"{CHECKPOINTS_PREFIX}{bullets}",
                "cache_control": {"type": "ephemeral"},
            }
        ],
    }


def build_layer2_message(ledger: str) -> dict[str, Any]:
    """L2b — mutable architectural ledger, replaced on each compaction."""
    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"{LEDGER_PREFIX}{ledger}",
                "cache_control": {"type": "ephemeral"},
            }
        ],
    }


def build_optimized_messages(session: SessionState, user_prompt: str) -> list[dict[str, Any]]:
    """
    Assemble the index-aligned payload:
      [0] L1  Claude.md (static, cached)
      [1] L2a Checkpoints (append-only, cached)  — only present when pins exist
      [*] L2b Ledger (mutable, cached)
      [*] L3  Rolling recent turns
      [-1] L4 Fresh user prompt
    """
    messages: list[dict[str, Any]] = [build_layer1_message()]
    if session.pinned_checkpoints:
        messages.append(build_layer2a_message(session.pinned_checkpoints))
    messages.append(build_layer2_message(session.history_ledger))
    messages.extend(session.rolling_recent_turns)
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _message_chars(msg: dict[str, Any]) -> int:
    return len(normalize_content(msg.get("content", "")))


def _est_history_tokens(session: SessionState) -> int:
    """Ledger + rolling window — used for token-based compaction trigger."""
    layer3_chars = sum(_message_chars(turn) for turn in session.rolling_recent_turns)
    ledger_chars = len(session.history_ledger) + len(LEDGER_PREFIX)
    return estimate_tokens(layer3_chars + ledger_chars)


def _trim_layer3(session: SessionState) -> None:
    max_messages = MAX_LAYER3_TURNS * 2
    if len(session.rolling_recent_turns) > max_messages:
        session.rolling_recent_turns = session.rolling_recent_turns[-max_messages:]


def _compaction_due(session: SessionState) -> tuple[bool, str | None]:
    if session.compaction_in_flight:
        return False, None
    if session.turn_counter < 1:
        return False, None
    if session.turn_counter >= MAX_TURNS_THRESHOLD:
        return True, "turn_threshold"
    if COMPACTION_TOKEN_THRESHOLD > 0 and _est_history_tokens(session) >= COMPACTION_TOKEN_THRESHOLD:
        return True, "token_threshold"
    return False, None


def build_context_snapshot(
    session: SessionState,
    user_prompt: str,
    incoming_messages: list[dict[str, Any]],
    *,
    stream: bool,
    max_tokens: int,
) -> ContextSnapshot:
    layer3_chars = sum(_message_chars(turn) for turn in session.rolling_recent_turns)
    naive_client_chars = sum(_message_chars(m) for m in incoming_messages)
    checkpoint_chars = sum(len(c.text) for c in session.pinned_checkpoints)
    return ContextSnapshot(
        layer1_chars=len(CLAUDE_MD_CONTENT),
        ledger_chars=len(session.history_ledger) + len(LEDGER_PREFIX),
        layer3_chars=layer3_chars,
        layer3_messages=len(session.rolling_recent_turns),
        prompt_chars=len(user_prompt),
        client_message_count=len(incoming_messages),
        ignored_messages=max(0, len(incoming_messages) - 1),
        naive_client_chars=naive_client_chars,
        pinned_checkpoints=len(session.pinned_checkpoints),
        checkpoint_chars=checkpoint_chars,
        turn_number=session.turn_counter + 1,
        lifetime_turn=session.lifetime_turns + 1,
        turns_until_compaction=max(0, MAX_TURNS_THRESHOLD - session.turn_counter - 1),
        max_turns_threshold=MAX_TURNS_THRESHOLD,
        max_layer3_turns=MAX_LAYER3_TURNS,
        compaction_token_threshold=COMPACTION_TOKEN_THRESHOLD,
        est_history_tokens=_est_history_tokens(session),
        stream=stream,
        max_tokens=max_tokens,
    )


def resolve_developer_id(request: Request) -> str:
    value = request.headers.get("x-developer-id")
    if value:
        return value.strip()
    return os.environ.get("TELEMETRY_DEVELOPER_ID", "unknown")


def detect_client(request: Request) -> str:
    ua = (request.headers.get("user-agent") or "").lower()
    if "vscode" in ua or "visual studio code" in ua:
        return "vscode"
    if "cursor" in ua:
        return "cursor"
    if "jetbrains" in ua:
        return "jetbrains"
    if "claude" in ua or "anthropic" in ua:
        return "claude-cli"
    return request.headers.get("x-client", "unknown")


def _log_incoming_api(request: Request, path: str, *, extra: str = "") -> None:
    if not _access_log_enabled():
        return
    suffix = f" {extra}" if extra else ""
    print(
        f"[PROXY] → {request.method} {path} client={_client_ip(request)} "
        f"ua={_ua_short(request)}{suffix}",
        flush=True,
    )


def record_telemetry(
    *,
    usage: Any,
    elapsed_time: float,
    session_id: str,
    developer_id: str,
    model: str,
    context: ContextSnapshot,
    compaction_triggered: bool,
    client: str,
) -> None:
    snap = UsageSnapshot.from_api(usage)
    cost = compute_costs(snap)
    synthesis = compute_synthesis_metrics(snap, context)
    print_telemetry_report(
        snap,
        cost,
        elapsed_time=elapsed_time,
        session_id=session_id,
        developer_id=developer_id,
        context=context,
        synthesis=synthesis,
    )
    try:
        append_event(
            TelemetryEvent(
                ts=utc_now_iso(),
                source="proxy",
                developer_id=developer_id,
                session_id=session_id,
                model=model,
                latency_s=elapsed_time,
                usage=snap,
                cost=cost,
                turn_number=context.turn_number,
                layer3_messages=context.layer3_messages,
                compaction_triggered=compaction_triggered,
                client=client,
                context=context,
                synthesis=synthesis,
            )
        )
    except OSError as exc:
        print(f"[TELEMETRY] Failed to append event: {exc}")


def record_compaction_telemetry(
    *,
    usage: Any,
    elapsed_time: float,
    session_id: str,
    developer_id: str,
    turns_compacted: int,
    ledger_chars_before: int,
    ledger_chars_after: int,
    pins_active: int = 0,
    trigger_reason: str = "turn_threshold",
) -> None:
    snap = UsageSnapshot.from_api(usage)
    cost = compute_costs(snap)
    try:
        append_event(
            TelemetryEvent(
                ts=utc_now_iso(),
                source="compaction",
                developer_id=developer_id,
                session_id=session_id,
                model=COMPACTION_MODEL,
                latency_s=elapsed_time,
                usage=snap,
                cost=cost,
                client="proxy",
                extra={
                    "turns_compacted": turns_compacted,
                    "ledger_chars_before": ledger_chars_before,
                    "ledger_chars_after": ledger_chars_after,
                    "ledger_delta_chars": ledger_chars_after - ledger_chars_before,
                    "pins_active": pins_active,
                    "trigger_reason": trigger_reason,
                    "dreaming_version": "v4",
                },
            )
        )
    except OSError as exc:
        print(f"[TELEMETRY] Failed to append compaction event: {exc}")


async def dream_compact(
    session_id: str,
    turns_snapshot: list[dict[str, Any]],
    ledger_snapshot: str,
    *,
    pins_snapshot: list[Checkpoint] | None = None,
    developer_id: str = "unknown",
    api_key: str | None = None,
    trigger_reason: str = "turn_threshold",
) -> bool:
    """Background synthesis: merge sliding-window turns into the history ledger.

    Pins (L2a checkpoints) are passed to Haiku as context so it doesn't
    waste ledger budget re-summarising already-guaranteed facts.
    """
    if not turns_snapshot:
        return False

    pins_snapshot = pins_snapshot or []
    print(
        f"[MEMORY MANAGER] Dreaming v4 for session {session_id} "
        f"({len(turns_snapshot)} msgs, trigger={trigger_reason}, "
        f"pins={len(pins_snapshot)})..."
    )
    ledger_chars_before = len(ledger_snapshot)
    key = api_key or DEFAULT_API_KEY
    if not key and not COPILOT_TOKEN:
        print(f"[MEMORY MANAGER] Skipping compaction for {session_id}: no API key available.")
        return False

    try:
        start_time = time.perf_counter()
        turns_text = format_turns_for_compaction(turns_snapshot, normalize_content)
        pin_texts = [c.text for c in pins_snapshot]
        prompt = build_compaction_prompt(ledger_snapshot, turns_text, pinned=pin_texts)
        response = await build_upstream(key).messages.create(
            model=COMPACTION_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed_time = time.perf_counter() - start_time
        new_ledger = extract_assistant_text(response.content).strip()
        if not new_ledger:
            print(f"[MEMORY MANAGER] Compaction produced empty ledger for {session_id}; keeping prior.")
            return False

        session = await get_session(session_id)
        async with session.lock:
            session.history_ledger = new_ledger
        print(f"[MEMORY MANAGER] Ledger updated for session {session_id} ({len(new_ledger):,} chars).")
        record_compaction_telemetry(
            usage=response.usage,
            elapsed_time=elapsed_time,
            session_id=session_id,
            developer_id=developer_id,
            turns_compacted=len(turns_snapshot) // 2,
            ledger_chars_before=ledger_chars_before,
            ledger_chars_after=len(new_ledger),
            pins_active=len(pins_snapshot),
            trigger_reason=trigger_reason,
        )
        return True
    except Exception as exc:
        print(f"[MEMORY MANAGER] Compaction failed for {session_id}: {exc}")
        return False


async def maybe_trigger_compaction(
    session_id: str,
    session: SessionState,
    *,
    developer_id: str,
) -> bool:
    due, reason = _compaction_due(session)
    if not due or reason is None:
        return False

    turns_snapshot = list(session.rolling_recent_turns)
    ledger_snapshot = session.history_ledger
    pins_snapshot = list(session.pinned_checkpoints)
    session.compaction_in_flight = True

    print(f"[MEMORY MANAGER] Compaction due ({reason}) for session {session_id}. Dreaming in background...")

    async def finalize_compaction() -> None:
        try:
            ok = await dream_compact(
                session_id,
                turns_snapshot,
                ledger_snapshot,
                pins_snapshot=pins_snapshot,
                developer_id=developer_id,
                api_key=session.api_key,
                trigger_reason=reason,
            )
            async with session.lock:
                if ok:
                    session.rolling_recent_turns.clear()
                    session.turn_counter = 0
        finally:
            async with session.lock:
                session.compaction_in_flight = False

    asyncio.create_task(finalize_compaction())
    return True


async def record_exchange(
    session: SessionState,
    user_prompt: str,
    assistant_text: str,
    session_id: str,
    *,
    developer_id: str,
) -> bool:
    async with session.lock:
        # Extract @synth-remember: pins before adding to L3.
        # Pinned lines are removed from the stored turn so they live exclusively
        # in L2a and are not subject to Dreaming summarisation.
        pins, clean_prompt = extract_pins(user_prompt)
        if pins:
            now = utc_now_iso()
            for pin_text in pins:
                session.pinned_checkpoints.append(
                    Checkpoint(text=pin_text, turn=session.lifetime_turns + 1, ts=now)
                )
            # LRU eviction: keep the most recent MAX_CHECKPOINTS pins
            if len(session.pinned_checkpoints) > MAX_CHECKPOINTS:
                session.pinned_checkpoints = session.pinned_checkpoints[-MAX_CHECKPOINTS:]
            print(
                f"[CHECKPOINT] +{len(pins)} pin(s) for {session_id} "
                f"(total={len(session.pinned_checkpoints)}): {pins}"
            )

        stored_prompt = clean_prompt.strip() or user_prompt
        session.rolling_recent_turns.append({"role": "user", "content": stored_prompt})
        session.rolling_recent_turns.append({"role": "assistant", "content": assistant_text})
        _trim_layer3(session)
        session.turn_counter += 1
        session.lifetime_turns += 1
        return await maybe_trigger_compaction(session_id, session, developer_id=developer_id)


def resolve_session_id(request: Request) -> str:
    for header in ("x-session-id", "session-id", "x-jetbrains-session-id"):
        value = request.headers.get(header)
        if value:
            return value.strip()
    return "default"


def api_kwargs_from_body(body: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": body.get("model", DEFAULT_MODEL),
        "max_tokens": body.get("max_tokens", 8192),
        "messages": messages,
    }
    for key in ("temperature", "top_p", "top_k", "stop_sequences", "metadata", "system"):
        if key in body and body[key] is not None:
            kwargs[key] = body[key]
    return kwargs


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — does not write telemetry."""
    return {"status": "ok", "service": "context-synthesizer"}


# ── OpenAI-compatible shim ────────────────────────────────────────────────────
# Allows Cursor (and any OpenAI-compatible client) to use the proxy as a
# custom model endpoint.  Format differences from the Anthropic API:
#   • Endpoint:   /v1/chat/completions  (not /v1/messages)
#   • System msg: inline role="system" message  (not top-level field)
#   • SSE chunks: OpenAI delta format  (not Anthropic event types)
#   • Response:   choices[0].message.content  (not content[0].text)
# The proxy logic (session state, compaction, telemetry) is identical.


def _normalize_oai_content(content: Any) -> str:
    """OpenAI messages can carry content as a plain string or a list of parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text") or "")
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(p for p in parts if p)
    return str(content) if content else ""


def _oai_body_to_anthropic(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """
    Convert an OpenAI chat-completions body into (user_prompt, extra_api_kwargs).

    Extracts the last user message as the fresh prompt and promotes any
    role='system' messages to the Anthropic top-level 'system' field.
    """
    messages: list[dict[str, Any]] = body.get("messages") or []

    system_parts = [
        _normalize_oai_content(m.get("content", ""))
        for m in messages if m.get("role") == "system"
    ]
    system_text = "\n\n".join(p for p in system_parts if p)

    user_prompt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_prompt = _normalize_oai_content(m.get("content", ""))
            break

    extra: dict[str, Any] = {}
    if system_text:
        extra["system"] = system_text
    for key in ("temperature", "top_p"):
        if key in body and body[key] is not None:
            extra[key] = body[key]
    stop = body.get("stop")
    if stop is not None:
        extra["stop_sequences"] = [stop] if isinstance(stop, str) else stop

    return user_prompt, extra


def _anthropic_to_oai_response(response: Any, model: str) -> dict[str, Any]:
    text = extract_assistant_text(response.content)
    usage = response.usage
    stop_reason = getattr(response, "stop_reason", "end_turn") or "end_turn"
    finish = "stop" if stop_reason in ("end_turn", "stop_sequence") else stop_reason
    return {
        "id": f"chatcmpl-synth-{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish,
            }
        ],
        "usage": {
            "prompt_tokens": int(getattr(usage, "input_tokens", 0)),
            "completion_tokens": int(getattr(usage, "output_tokens", 0)),
            "total_tokens": int(
                getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)
            ),
        },
    }


async def _handle_streaming_oai(
    *,
    upstream: AsyncAnthropic,
    api_kwargs: dict[str, Any],
    session: SessionState,
    session_id: str,
    developer_id: str,
    client_name: str,
    user_prompt: str,
    context_snapshot: "ContextSnapshot",
    model: str,
) -> StreamingResponse:
    start_time = time.perf_counter()
    chunk_id = f"chatcmpl-synth-{int(time.time() * 1000)}"
    created = int(time.time())

    def _chunk(delta: dict[str, Any], finish: str | None = None) -> str:
        return (
            "data: "
            + json.dumps(
                {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                },
                ensure_ascii=False,
            )
            + "\n\n"
        )

    async def event_generator():
        assistant_text = ""
        usage = None
        compaction = False

        # Role header chunk (OpenAI convention)
        yield _chunk({"role": "assistant", "content": ""})

        try:
            async with upstream.messages.stream(**api_kwargs) as stream:
                async for text in stream.text_stream:
                    assistant_text += text
                    yield _chunk({"content": text})
                final_message = await stream.get_final_message()
                usage = final_message.usage
        except Exception as exc:
            yield (
                "data: "
                + json.dumps({"error": {"message": str(exc), "type": "proxy_error"}})
                + "\n\n"
            )
            return

        yield _chunk({}, "stop")
        yield "data: [DONE]\n\n"

        elapsed_time = time.perf_counter() - start_time
        if assistant_text:
            compaction = await record_exchange(
                session, user_prompt, assistant_text, session_id, developer_id=developer_id
            )
        if usage:
            record_telemetry(
                usage=usage,
                elapsed_time=elapsed_time,
                session_id=session_id,
                developer_id=developer_id,
                model=model,
                context=context_snapshot,
                compaction_triggered=compaction,
                client=client_name,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    """OpenAI-compatible model list — Cursor uses this to populate the model picker."""
    from models import AVAILABLE_MODELS, DEFAULT_CHAT_MODEL
    data = [
        {
            "id": m,
            "object": "model",
            "created": 1_700_000_000,
            "owned_by": "anthropic",
        }
        for m in AVAILABLE_MODELS
    ]
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """OpenAI-compatible chat completions — for Cursor and other OpenAI-format clients."""
    _log_incoming_api(request, "/v1/chat/completions")
    body = await request.json()
    messages: list[dict[str, Any]] = body.get("messages") or []
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    session_id = resolve_session_id(request)
    developer_id = resolve_developer_id(request)
    client_name = detect_client(request)
    api_key = resolve_api_key(request)
    if not api_key and not COPILOT_TOKEN:
        print(
            f"[PROXY] ✗ POST /v1/chat/completions rejected: no API key "
            f"client={_client_ip(request)}",
            flush=True,
        )
        raise HTTPException(
            status_code=401,
            detail=(
                "Missing API key. In Cursor Settings → Models → your custom model, "
                "set the API key to your Anthropic key."
            ),
        )

    user_prompt, extra_kwargs = _oai_body_to_anthropic(body)
    if not user_prompt.strip():
        raise HTTPException(status_code=400, detail="Latest user message is empty")

    session = await get_session(session_id)
    async with session.lock:
        session.api_key = api_key

    async with session.lock:
        optimized_messages = build_optimized_messages(session, user_prompt)

    model = body.get("model", DEFAULT_MODEL)
    max_tokens = int(body.get("max_tokens") or 8192)
    api_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": optimized_messages,
        **extra_kwargs,
    }

    stream_requested = bool(body.get("stream"))
    context_snapshot = build_context_snapshot(
        session,
        user_prompt,
        messages,
        stream=stream_requested,
        max_tokens=max_tokens,
    )
    upstream = build_upstream(api_key)

    if stream_requested:
        return await _handle_streaming_oai(
            upstream=upstream,
            api_kwargs=api_kwargs,
            session=session,
            session_id=session_id,
            developer_id=developer_id,
            client_name=client_name,
            user_prompt=user_prompt,
            context_snapshot=context_snapshot,
            model=model,
        )

    start_time = time.perf_counter()
    try:
        response = await upstream.messages.create(**api_kwargs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {exc}") from exc
    elapsed_time = time.perf_counter() - start_time

    assistant_text = extract_assistant_text(response.content)
    compaction = await record_exchange(
        session, user_prompt, assistant_text, session_id, developer_id=developer_id
    )
    record_telemetry(
        usage=response.usage,
        elapsed_time=elapsed_time,
        session_id=session_id,
        developer_id=developer_id,
        model=model,
        context=context_snapshot,
        compaction_triggered=compaction,
        client=client_name,
    )
    return JSONResponse(content=_anthropic_to_oai_response(response, model))


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    _log_incoming_api(request, "/v1/messages")
    body = await request.json()
    incoming_messages = body.get("messages", [])
    if not incoming_messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    session_id = resolve_session_id(request)
    developer_id = resolve_developer_id(request)
    client_name = detect_client(request)
    api_key = resolve_api_key(request)
    if not api_key and not COPILOT_TOKEN:
        print(
            f"[PROXY] ✗ POST /v1/messages rejected: no API key "
            f"client={_client_ip(request)} — VS Code needs claudeCode.environmentVariables "
            f"or ~/.claude/settings.json",
            flush=True,
        )
        raise HTTPException(
            status_code=401,
            detail=(
                "Missing Anthropic API key. Add ANTHROPIC_API_KEY to ~/.claude/settings.json "
                "(Claude CLI forwards it as x-api-key) or set ANTHROPIC_API_KEY in the proxy environment."
            ),
        )

    session = await get_session(session_id)
    async with session.lock:
        session.api_key = api_key
    user_prompt = normalize_content(incoming_messages[-1].get("content"))
    if not user_prompt.strip():
        raise HTTPException(status_code=400, detail="Latest user message is empty")

    async with session.lock:
        optimized_messages = build_optimized_messages(session, user_prompt)

    upstream = build_upstream(api_key)

    api_kwargs = api_kwargs_from_body(body, optimized_messages)
    stream_requested = bool(body.get("stream"))
    context_snapshot = build_context_snapshot(
        session,
        user_prompt,
        incoming_messages,
        stream=stream_requested,
        max_tokens=int(api_kwargs.get("max_tokens") or 0),
    )

    if stream_requested:
        return await _handle_streaming(
            upstream=upstream,
            api_kwargs=api_kwargs,
            session=session,
            session_id=session_id,
            developer_id=developer_id,
            client_name=client_name,
            user_prompt=user_prompt,
            context_snapshot=context_snapshot,
        )

    start_time = time.perf_counter()
    try:
        response = await upstream.messages.create(**api_kwargs)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {exc}") from exc
    elapsed_time = time.perf_counter() - start_time

    assistant_text = extract_assistant_text(response.content)
    compaction = await record_exchange(
        session, user_prompt, assistant_text, session_id, developer_id=developer_id
    )
    record_telemetry(
        usage=response.usage,
        elapsed_time=elapsed_time,
        session_id=session_id,
        developer_id=developer_id,
        model=api_kwargs.get("model", DEFAULT_MODEL),
        context=context_snapshot,
        compaction_triggered=compaction,
        client=client_name,
    )

    return JSONResponse(content=response.model_dump())


async def _handle_streaming(
    *,
    upstream: AsyncAnthropic,
    api_kwargs: dict[str, Any],
    session: SessionState,
    session_id: str,
    developer_id: str,
    client_name: str,
    user_prompt: str,
    context_snapshot: ContextSnapshot,
) -> StreamingResponse:
    start_time = time.perf_counter()

    async def event_generator():
        assistant_text = ""
        usage = None
        try:
            async with upstream.messages.stream(**api_kwargs) as stream:
                async for event in stream:
                    payload = event.model_dump() if hasattr(event, "model_dump") else dict(event)
                    event_type = payload.get("type", "unknown")
                    yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

                final_message = await stream.get_final_message()
                assistant_text = extract_assistant_text(final_message.content)
                usage = final_message.usage
        except Exception as exc:
            error_payload = {"type": "error", "error": {"type": "proxy_error", "message": str(exc)}}
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
            return

        elapsed_time = time.perf_counter() - start_time
        compaction = False
        if assistant_text:
            compaction = await record_exchange(
                session, user_prompt, assistant_text, session_id, developer_id=developer_id
            )
        if usage:
            record_telemetry(
                usage=usage,
                elapsed_time=elapsed_time,
                session_id=session_id,
                developer_id=developer_id,
                model=api_kwargs.get("model", DEFAULT_MODEL),
                context=context_snapshot,
                compaction_triggered=compaction,
                client=client_name,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


if __name__ == "__main__":
    import sys

    host = os.environ.get("PROXY_HOST", "127.0.0.1")
    port = int(os.environ.get("PROXY_PORT", "8080"))
    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as exc:
        print(f"[PROXY] Failed to bind {host}:{port}: {exc}", file=sys.stderr)
        if getattr(exc, "errno", None) in (98, 10048) or "address already in use" in str(exc).lower():
            print(
                f"[PROXY] Port {port} is in use. Stop the other process or set "
                f"PROXY_PORT=8081 in context-synthesizer/.env and update ANTHROPIC_BASE_URL.",
                file=sys.stderr,
            )
        raise SystemExit(1) from exc
