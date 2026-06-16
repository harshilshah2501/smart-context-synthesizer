"""
Dreaming v4 — code-aware context compaction for the history ledger.

Pre-processes tool-heavy turns before Haiku synthesis and applies ledger rules
learned from long-session corpus analysis (file re-reads, Bash bloat, Read dedup).
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Per-block limits when feeding turns into the compaction model
MAX_BASH_BLOCK_CHARS = 400
MAX_TOOL_RESULT_CHARS = 800
MAX_TURN_BODY_CHARS = 12_000

# All recognised @synth-remember aliases (case-insensitive prefix match)
_PIN_MARKERS = (
    "@synth-remember:",
    "@remember:",
    "@pin:",
    "@must-remember:",
)

DREAMING_V4_RULES = """You are a code-aware context compaction engine (Dreaming v4).
Merge the recent conversation turns into an updated architectural history ledger.

PRESERVE (dense bullets):
- Key decisions, constraints, open tasks, API contracts
- File paths and what changed in each file (latest state only)
- Errors encountered and their resolution (one line each)
- Test/lint outcomes that affect next steps

CODE-AWARE COLLAPSE:
- Read / ReadFile: one bullet per path — "path: <current role or last change>" — never duplicate full file bodies
- Bash / Shell: outcome only — command + exit code + one-line result (drop stdout/stderr walls)
- Grep / Glob / Search: pattern + hit count + top paths — not full match dumps
- Edit / Write: path + what changed — not full diffs
- Repeated file touches: keep ONLY the latest state per path (State Override)

DROP:
- Redundant phrasing, repeated errors, boilerplate, pleasantries
- Verbose tool output already summarized above
- "Was X, now Y" history — write only the current state

OUTPUT:
- Dense bulleted ledger body only
- Max ~2,000 tokens
- No preamble, no markdown fences"""


def extract_pins(text: str) -> tuple[list[str], str]:
    """
    Scan text for @synth-remember: (and aliases) lines.

    Returns (pin_texts, text_with_pin_lines_removed).
    Pin lines are stripped from the turn so they don't consume L3 space
    and instead live exclusively in the pinned-checkpoints block (L2a).
    """
    pins: list[str] = []
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        matched = False
        for marker in _PIN_MARKERS:
            if stripped.lower().startswith(marker):
                pin_text = stripped[len(marker):].strip()
                if pin_text:
                    pins.append(pin_text)
                matched = True
                break
        if not matched:
            kept.append(line)
    return pins, "\n".join(kept)


def _collapse_bash_blocks(text: str) -> str:
    """Truncate long shell output blocks likely to dominate compaction input."""
    lines = text.splitlines()
    out: list[str] = []
    in_bash = False
    bash_buf: list[str] = []

    def flush_bash() -> None:
        nonlocal bash_buf, in_bash
        if not bash_buf:
            return
        block = "\n".join(bash_buf)
        if len(block) > MAX_BASH_BLOCK_CHARS:
            block = block[:MAX_BASH_BLOCK_CHARS] + f"\n… [bash output truncated, {len(bash_buf)} lines]"
        out.append(block)
        bash_buf = []
        in_bash = False

    for line in lines:
        lower = line.lower()
        if re.match(r"^\$ |^```(?:bash|sh|shell)|^Command:|^Exit code:", line) or "bash" in lower[:40]:
            flush_bash()
            in_bash = True
            bash_buf.append(line)
        elif in_bash and (line.startswith(" ") or line.startswith("\t") or len(bash_buf) < 30):
            bash_buf.append(line)
        else:
            flush_bash()
            out.append(line)
    flush_bash()
    return "\n".join(out)


def _dedupe_file_mentions(text: str) -> str:
    """Collapse consecutive duplicate path lines (common after re-reads)."""
    path_re = re.compile(r"(/[\w./-]+\.(?:py|tsx?|jsx?|md|json|yaml|yml|go|rs|java))\b")
    seen_paths: set[str] = set()
    out: list[str] = []
    for line in text.splitlines():
        paths = path_re.findall(line)
        if paths and all(p in seen_paths for p in paths):
            continue
        for p in paths:
            seen_paths.add(p)
        out.append(line)
    return "\n".join(out)


def prepare_turn_text(text: str) -> str:
    if len(text) <= MAX_TURN_BODY_CHARS:
        collapsed = _collapse_bash_blocks(text)
        return _dedupe_file_mentions(collapsed)
    head = text[: MAX_TURN_BODY_CHARS // 2]
    tail = text[-MAX_TURN_BODY_CHARS // 4 :]
    mid = f"\n… [middle truncated, {len(text):,} chars total]\n"
    return _dedupe_file_mentions(_collapse_bash_blocks(head + mid + tail))


def format_turns_for_compaction(
    turns: list[dict[str, Any]],
    normalize_content: Callable[[Any], str],
) -> str:
    lines: list[str] = []
    for turn in turns:
        role = turn.get("role", "unknown")
        raw = normalize_content(turn.get("content", ""))
        text = prepare_turn_text(raw)
        if len(text) > MAX_TOOL_RESULT_CHARS and role != "user":
            text = text[:MAX_TOOL_RESULT_CHARS] + f"\n… [truncated to {MAX_TOOL_RESULT_CHARS} chars]"
        lines.append(f"[{role.upper()}]\n{text}\n")
    return "\n".join(lines)


def build_compaction_prompt(
    ledger: str,
    turns_text: str,
    *,
    pinned: list[str] | None = None,
) -> str:
    """
    Build the Haiku synthesis prompt.

    pinned: list of already-pinned checkpoint texts (L2a). Haiku is told these
    are preserved separately so it doesn't need to re-summarise them into the ledger.
    """
    pinned_section = ""
    if pinned:
        bullets = "\n".join(f"- {p}" for p in pinned)
        pinned_section = (
            "\nPINNED CHECKPOINTS (guaranteed preserved in L2a — "
            "do NOT duplicate these in your ledger output):\n"
            f"{bullets}\n\n"
        )
    return (
        f"{DREAMING_V4_RULES}\n\n"
        f"CURRENT LEDGER:\n{ledger}\n\n"
        f"{pinned_section}"
        f"TURNS TO COMPACT:\n{turns_text}"
    )
