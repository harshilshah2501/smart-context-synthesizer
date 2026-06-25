"""Shared pytest fixtures for FastAPI route tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("CLAUDE_MD_PATH", str(_ROOT / "Claude.md"))
os.environ.setdefault("TELEMETRY_LOG_PATH", str(_ROOT / "stats" / "test-telemetry.jsonl"))


@pytest.fixture
def client() -> TestClient:
    from proxy_tool import app

    with TestClient(app) as test_client:
        yield test_client
