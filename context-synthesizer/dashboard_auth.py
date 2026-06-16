"""Optional auth for dashboard routes when the proxy binds beyond localhost."""

from __future__ import annotations

import os
from ipaddress import ip_address

from fastapi import HTTPException, Request

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def dashboard_token() -> str:
    return os.environ.get("DASHBOARD_TOKEN", "").strip()


def dashboard_localhost_only() -> bool:
    return _truthy(os.environ.get("DASHBOARD_LOCALHOST_ONLY"))


def dashboard_auth_required() -> bool:
    if dashboard_localhost_only():
        return True
    if dashboard_token():
        return True
    # Wide bind without token — warn at startup; require token when explicitly set.
    return False


def _client_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


def _is_loopback(host: str) -> bool:
    if not host or host in _LOOPBACK:
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _token_from_request(request: Request) -> str:
    query = request.query_params.get("token", "").strip()
    if query:
        return query
    header = request.headers.get("x-dashboard-token", "").strip()
    if header:
        return header
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def verify_dashboard_access(request: Request) -> None:
    host = _client_host(request)

    if dashboard_localhost_only() and not _is_loopback(host):
        raise HTTPException(
            status_code=403,
            detail="Dashboard is localhost-only (DASHBOARD_LOCALHOST_ONLY=1).",
        )

    expected = dashboard_token()
    if not expected:
        return

    provided = _token_from_request(request)
    if provided != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing dashboard token. Use ?token= from open_dashboard.sh.",
        )
