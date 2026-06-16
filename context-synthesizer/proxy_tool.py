"""
Local API gateway proxy for JetBrains IDE → Anthropic with index-aligned prompt caching.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import uvicorn
from anthropic import AsyncAnthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from dashboard_routes import attach_dashboard
from compaction import build_compaction_prompt, format_turns_for_compaction
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

app = FastAPI(title="Context Synthesizer Proxy")
attach_dashboard(app)

DEFAULT_CLAUDE_MD_PATH = Path(__file__).resolve().parent / "Claude.md"
CLAUDE_MD_PATH = Path(os.environ.get("CLAUDE_MD_PATH", str(DEFAULT_CLAUDE_MD_PATH)))
MAX_TURNS_THRESHOLD = int(os.environ.get("MAX_TURNS_THRESHOLD", "10"))
MAX_LAYER3_TURNS = int(os.environ.get("MAX_LAYER3_TURNS", str(MAX_TURNS_THRESHOLD)))
COMPACTION_TOKEN_THRESHOLD = int(os.environ.get("COMPACTION_TOKEN_THRESHOLD", "100000"))
DEFAULT_MODEL = DEFAULT_CHAT_MODEL
COMPACTION_MODEL = DEFAULT_COMPACTION_MODEL
LEDGER_PREFIX = "Current Architectural State:\n"

CLAUDE_MD_CONTENT: str = ""
DEFAULT_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip() or None

_sessions: dict[str, "SessionState"] = {}
_sessions_lock = asyncio.Lock()


@dataclass
class SessionState:
    history_ledger: str = "Initial State: System active and optimized."
    rolling_recent_turns: list[dict[str, Any]] = field(default_factory=list)
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


def build_layer2_message(ledger: str) -> dict[str, Any]:
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
    messages: list[dict[str, Any]] = [
        build_layer1_message(),
        build_layer2_message(session.history_ledger),
    ]
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
    return ContextSnapshot(
        layer1_chars=len(CLAUDE_MD_CONTENT),
        ledger_chars=len(session.history_ledger) + len(LEDGER_PREFIX),
        layer3_chars=layer3_chars,
        layer3_messages=len(session.rolling_recent_turns),
        prompt_chars=len(user_prompt),
        client_message_count=len(incoming_messages),
        ignored_messages=max(0, len(incoming_messages) - 1),
        naive_client_chars=naive_client_chars,
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
    if "jetbrains" in ua:
        return "jetbrains"
    if "claude" in ua or "anthropic" in ua:
        return "claude-cli"
    return request.headers.get("x-client", "unknown")


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
    developer_id: str = "unknown",
    api_key: str | None = None,
    trigger_reason: str = "turn_threshold",
) -> bool:
    """Background synthesis: merge sliding-window turns into the history ledger."""
    if not turns_snapshot:
        return False

    print(
        f"[MEMORY MANAGER] Dreaming v4 for session {session_id} "
        f"({len(turns_snapshot)} msgs, trigger={trigger_reason})..."
    )
    ledger_chars_before = len(ledger_snapshot)
    key = api_key or DEFAULT_API_KEY
    if not key:
        print(f"[MEMORY MANAGER] Skipping compaction for {session_id}: no API key available.")
        return False

    try:
        start_time = time.perf_counter()
        turns_text = format_turns_for_compaction(turns_snapshot, normalize_content)
        prompt = build_compaction_prompt(ledger_snapshot, turns_text)
        response = await anthropic_client(key).messages.create(
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
    session.compaction_in_flight = True

    print(f"[MEMORY MANAGER] Compaction due ({reason}) for session {session_id}. Dreaming in background...")

    async def finalize_compaction() -> None:
        try:
            ok = await dream_compact(
                session_id,
                turns_snapshot,
                ledger_snapshot,
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
        session.rolling_recent_turns.append({"role": "user", "content": user_prompt})
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


@app.on_event("startup")
async def startup() -> None:
    global CLAUDE_MD_CONTENT
    CLAUDE_MD_CONTENT = load_claude_md()
    from dashboard_auth import dashboard_localhost_only, dashboard_token
    from telemetry import TELEMETRY_LOG_PATH

    l1_est = estimate_tokens(len(CLAUDE_MD_CONTENT))
    print(f"[PROXY] Loaded Claude.md from {CLAUDE_MD_PATH} ({len(CLAUDE_MD_CONTENT):,} chars, ~{l1_est:,} tok est.)")
    if l1_est < MIN_CACHE_TOKENS:
        print(
            f"[PROXY] ⚠ Layer 1 below {MIN_CACHE_TOKENS:,} token cache minimum. "
            "Run build_production_claude_md.py and set CLAUDE_MD_PATH."
        )
    print(f"[PROXY] Chat model: {DEFAULT_MODEL} | Compaction model: {COMPACTION_MODEL}")
    print(
        f"[PROXY] Compaction: every {MAX_TURNS_THRESHOLD} turns | "
        f"Layer3 cap {MAX_LAYER3_TURNS} turns | "
        f"token threshold {COMPACTION_TOKEN_THRESHOLD:,} (0=off)"
    )
    print(f"[PROXY] Telemetry log: {TELEMETRY_LOG_PATH}")
    print("[PROXY] Auth: Claude CLI BYOK (x-api-key per request) or ANTHROPIC_API_KEY env fallback")
    host = os.environ.get("PROXY_HOST", "127.0.0.1")
    port = os.environ.get("PROXY_PORT", "8080")
    dash_url = f"http://{host}:{port}/dashboard"
    if dashboard_token():
        dash_url += "?token=<DASHBOARD_TOKEN>"
    print(f"[PROXY] Live dashboard: {dash_url}")
    if host == "0.0.0.0" and not dashboard_token() and not dashboard_localhost_only():
        print(
            "[PROXY] ⚠ PROXY_HOST=0.0.0.0 without DASHBOARD_TOKEN — "
            "dashboard is reachable on your LAN. Set DASHBOARD_TOKEN in .env or re-run setup."
        )
    if dashboard_localhost_only():
        print("[PROXY] Dashboard: localhost-only (DASHBOARD_LOCALHOST_ONLY=1)")
    elif dashboard_token():
        print("[PROXY] Dashboard: token required (DASHBOARD_TOKEN set)")


@app.post("/v1/messages")
async def proxy_messages(request: Request):
    body = await request.json()
    incoming_messages = body.get("messages", [])
    if not incoming_messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    session_id = resolve_session_id(request)
    developer_id = resolve_developer_id(request)
    client_name = detect_client(request)
    api_key = resolve_api_key(request)
    if not api_key:
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

    upstream = anthropic_client(api_key)

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
