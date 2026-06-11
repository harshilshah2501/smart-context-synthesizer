"""
Anthropic model IDs — synced with GET /v1/models on your account.

Override at runtime:
  export ANTHROPIC_MODEL=claude-fable-5
  export COMPACTION_MODEL=claude-haiku-4-5-20251001
"""

from __future__ import annotations

import os

# All models returned by your API key (2026-06-10)
AVAILABLE_MODELS: tuple[str, ...] = (
    "claude-fable-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-opus-4-5-20251101",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
)

# Role-based defaults (override via env)
DEFAULT_CHAT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
DEFAULT_COMPACTION_MODEL = os.environ.get("COMPACTION_MODEL", "claude-haiku-4-5-20251001")

# Quick reference for operators
MODEL_ROLES: dict[str, str] = {
    "claude-sonnet-4-6": "Default chat — 1M context, compact support, best speed/cost balance",
    "claude-fable-5": "Frontier — 1M context, strongest general intelligence",
    "claude-opus-4-8": "Frontier — 1M context, long-running agents & coding",
    "claude-opus-4-7": "Frontier — 1M context, adaptive thinking",
    "claude-haiku-4-5-20251001": "Compaction / cheap tasks — background dreaming",
    "claude-sonnet-4-5-20250929": "Legacy Sonnet — 1M context",
}
