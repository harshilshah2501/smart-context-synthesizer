"""Tests for dashboard aggregation helpers."""

from __future__ import annotations

import proxy_tool
from dashboard_api import prefix_cache_status, recommendations


def test_prefix_cache_status_below_floor(monkeypatch):
    monkeypatch.setattr(proxy_tool, "CLAUDE_MD_CONTENT", "x" * 100)
    monkeypatch.setattr(proxy_tool, "_sessions", {})
    status = prefix_cache_status()
    assert status["below_floor"] is True
    assert status["est_prefix_tokens"] < status["min_cache_tokens"]


def test_prefix_cache_status_above_floor(monkeypatch):
    monkeypatch.setattr(proxy_tool, "CLAUDE_MD_CONTENT", "word " * 2000)
    monkeypatch.setattr(proxy_tool, "_sessions", {})
    status = prefix_cache_status()
    assert status["below_floor"] is False
    assert status["est_prefix_tokens"] >= status["min_cache_tokens"]


def test_recommendations_empty_proxy():
    recs = recommendations({"proxy_requests": 0})
    assert len(recs) == 1
    assert "No proxy events" in recs[0]
