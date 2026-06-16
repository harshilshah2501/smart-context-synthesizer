"""Live telemetry dashboard routes — mounted on the proxy FastAPI app."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from dashboard_api import dashboard_payload
from dashboard_auth import dashboard_token, verify_dashboard_access
from telemetry import TELEMETRY_LOG_PATH, get_live_events

STATIC_DIR = Path(__file__).resolve().parent / "static"
router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard_page(_: None = Depends(verify_dashboard_access)) -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html", media_type="text/html")


@router.get("/api/dashboard/meta")
async def dashboard_meta(_: None = Depends(verify_dashboard_access)) -> dict:
    return {
        "telemetry_log": str(TELEMETRY_LOG_PATH),
        "auth_required": bool(dashboard_token()),
        "endpoints": {
            "page": "/dashboard",
            "data": "/api/dashboard/data",
            "stream": "/api/dashboard/stream",
        },
    }


@router.get("/api/dashboard/data")
async def dashboard_data(
    _: None = Depends(verify_dashboard_access),
    limit: int = Query(500, ge=1, le=5000),
    developer_id: str | None = None,
    session_id: str | None = None,
    source: str | None = None,
    chart_points: int = Query(60, ge=10, le=200),
) -> dict:
    return dashboard_payload(
        limit=limit,
        developer_id=developer_id or None,
        session_id=session_id or None,
        source=source or None,
        chart_points=chart_points,
    )


@router.get("/api/dashboard/stream")
async def dashboard_stream(
    request: Request,
    _: None = Depends(verify_dashboard_access),
    since: int = Query(0, ge=0),
    developer_id: str | None = None,
    session_id: str | None = None,
) -> StreamingResponse:
    """Server-Sent Events — push new telemetry rows as they arrive."""

    async def event_generator():
        cursor = since
        while True:
            if await request.is_disconnected():
                break
            batch, total = get_live_events(since_index=cursor)
            if developer_id:
                batch = [e for e in batch if e.get("developer_id") == developer_id]
            if session_id:
                batch = [e for e in batch if e.get("session_id") == session_id]
            for ev in batch:
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            cursor = total
            yield f"event: ping\ndata: {json.dumps({'live_total': total})}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/api/checkpoints")
async def checkpoint_list(_: None = Depends(verify_dashboard_access)) -> dict:
    """Return live pinned checkpoints per active session."""
    try:
        from proxy_tool import _sessions
    except ImportError:
        return {"sessions": {}}
    result: dict[str, list[dict]] = {}
    for sid, state in _sessions.items():
        if state.pinned_checkpoints:
            result[sid] = [
                {"text": c.text, "turn": c.turn, "ts": c.ts}
                for c in state.pinned_checkpoints
            ]
    return {"sessions": result}


def attach_dashboard(app) -> None:
    app.include_router(router)
