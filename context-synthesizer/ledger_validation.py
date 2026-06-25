"""
Structured validation for Haiku compaction ledger output (L2).

Parses bullet ledgers, enforces programmatic state override (latest wins per
file path and core_stack key), and strips markdown fences before storage.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

PATH_RE = re.compile(
    r"(/[\w./-]+\.(?:py|tsx?|jsx?|md|json|yaml|yml|go|rs|java))\b"
)
BULLET_START_RE = re.compile(r"^\s*([-*•]|\d+\.)\s+")
FENCE_LINE_RE = re.compile(r"^```")
DEPRECATED_KEYWORDS = (
    "deprecated",
    "replaced with",
    "no longer use",
    "no longer used",
    "removed in favor",
    "superseded",
)
CONSTRAINT_MARKERS = (
    "must ",
    "never ",
    "always ",
    "do not ",
    "don't ",
    "required",
    "constraint",
)

MAX_LEDGER_CHARS = 16_000


class ArchitectureLedger(BaseModel):
    """Canonical L2 ledger sections derived from Haiku bullet output."""

    core_stack: dict[str, str] = Field(default_factory=dict)
    active_constraints: list[str] = Field(default_factory=list)
    deprecated_patterns: list[str] = Field(default_factory=list)
    file_state: dict[str, str] = Field(default_factory=dict)
    general: list[str] = Field(default_factory=list)

    @classmethod
    def from_bullets(cls, bullets: list[str]) -> ArchitectureLedger:
        ledger = cls()
        for bullet in bullets:
            ledger._ingest_bullet(bullet)
        return ledger

    def _ingest_bullet(self, bullet: str) -> None:
        text = _strip_bullet_marker(bullet).strip()
        if not text:
            return

        paths = PATH_RE.findall(text) or PATH_RE.findall(bullet)
        if paths:
            for path in sorted(set(paths)):
                self.file_state[path] = bullet.strip()
            return

        lower = text.lower()
        if any(keyword in lower for keyword in DEPRECATED_KEYWORDS):
            self.deprecated_patterns.append(bullet.strip())
            return

        if _looks_like_constraint(text):
            self.active_constraints.append(bullet.strip())
            return

        kv = _parse_kv_bullet(text)
        if kv is not None:
            key, value = kv
            self.core_stack[key] = value
            return

        self.general.append(bullet.strip())

    def to_ledger_text(self) -> str:
        lines: list[str] = []
        for key in sorted(self.core_stack):
            lines.append(f"- {key}: {self.core_stack[key]}")
        for path in sorted(self.file_state):
            text = self.file_state[path]
            lines.append(text if text.lstrip().startswith("-") else f"- {text}")
        for constraint in self.active_constraints:
            lines.append(
                constraint if constraint.lstrip().startswith("-") else f"- {constraint}"
            )
        for deprecated in self.deprecated_patterns:
            lines.append(
                deprecated if deprecated.lstrip().startswith("-") else f"- {deprecated}"
            )
        for item in self.general:
            lines.append(item if item.lstrip().startswith("-") else f"- {item}")
        return "\n".join(lines)


def _strip_bullet_marker(line: str) -> str:
    return BULLET_START_RE.sub("", line, count=1)


def _looks_like_constraint(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in CONSTRAINT_MARKERS)


def _parse_kv_bullet(text: str) -> tuple[str, str] | None:
    if ": " not in text:
        return None
    key, _, value = text.partition(": ")
    key = key.strip().lower()
    value = value.strip()
    if not key or not value:
        return None
    if len(key) > 48 or PATH_RE.search(key):
        return None
    if not re.match(r"^[\w][\w\s/-]*$", key):
        return None
    return key, value


def strip_markdown_fences(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if FENCE_LINE_RE.match(line.strip()):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def parse_ledger_bullets(text: str) -> list[str]:
    """Split ledger text into bullet blocks (supports -, *, •, numbered lists)."""
    bullets: list[str] = []
    current: list[str] = []

    for line in text.splitlines():
        if BULLET_START_RE.match(line):
            if current:
                bullets.append("\n".join(current).strip())
            current = [line.rstrip()]
        elif current and line.strip():
            current.append(line.rstrip())
        elif current and not line.strip():
            bullets.append("\n".join(current).strip())
            current = []
    if current:
        bullets.append("\n".join(current).strip())
    return [bullet for bullet in bullets if bullet]


def validate_and_normalize_ledger(raw: str, *, fallback: str | None = None) -> str:
    """
    Validate Haiku ledger output and return a canonical bullet ledger.

    Applies state override (latest bullet wins per file path and stack key),
    classifies constraints/deprecated lines, and strips markdown fences.
    """
    cleaned = strip_markdown_fences(raw.strip())
    if not cleaned:
        return (fallback or "").strip()

    bullets = parse_ledger_bullets(cleaned)
    if not bullets:
        return cleaned

    ledger = ArchitectureLedger.from_bullets(bullets)
    normalized = ledger.to_ledger_text()
    if not normalized.strip():
        return cleaned

    if len(normalized) > MAX_LEDGER_CHARS:
        normalized = normalized[:MAX_LEDGER_CHARS] + "\n… [ledger truncated]"
    return normalized
