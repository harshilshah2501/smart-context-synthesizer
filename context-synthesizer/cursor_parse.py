"""Shared Cursor agent-transcript parsing for Mode C tools."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from session_models import FileTouch, SessionAnalysis, TurnSnapshot

PATH_RE = re.compile(r"(?:/[\w.\-]+)+(?:/[\w.\-]+)*")
READ_TOOLS = frozenset({"Read", "ReadFile", "Grep", "rg", "Glob", "SemanticSearch"})


@dataclass
class ContentBlock:
    text: str = ""
    tool_name: str | None = None
    tool_input: dict | None = None


def blocks_from_record(record: dict) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    for item in record.get("message", {}).get("content") or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "text":
            blocks.append(ContentBlock(text=item.get("text") or ""))
        elif kind == "tool_use":
            blocks.append(
                ContentBlock(
                    text="",
                    tool_name=item.get("name"),
                    tool_input=item.get("input") if isinstance(item.get("input"), dict) else None,
                )
            )
    return blocks


def paths_from_tool_input(tool_input: dict | None) -> list[str]:
    if not tool_input:
        return []
    paths: list[str] = []
    for key in ("path", "target_directory", "glob_pattern", "working_directory"):
        val = tool_input.get(key)
        if isinstance(val, str) and ("/" in val or "\\" in val):
            paths.append(val)
    return paths


def paths_from_text(text: str) -> list[str]:
    return [m.group(0) for m in PATH_RE.finditer(text) if m.group(0).count("/") >= 2]


def find_transcript(
    cursor_root: Path,
    *,
    session_id: str | None,
    project: str | None,
    pick_largest: bool,
) -> Path | None:
    candidates: list[Path] = []
    for path in sorted(cursor_root.glob("**/agent-transcripts/**/*.jsonl")):
        if "subagents" in path.parts:
            continue
        if project and project not in str(path):
            continue
        if session_id and not (path.stem.startswith(session_id) or session_id in str(path)):
            continue
        candidates.append(path)

    if not candidates:
        return None
    if pick_largest or not session_id:
        return max(candidates, key=lambda p: p.stat().st_size)
    return candidates[0]


def analyze_transcript(
    path: Path,
    *,
    layer1_chars: int,
    ledger_chars: int,
    max_turns_threshold: int,
) -> SessionAnalysis | None:
    project_slug = path.parts[path.parts.index("projects") + 1] if "projects" in path.parts else "unknown"
    session_id = path.stem

    try:
        lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    except (OSError, json.JSONDecodeError):
        return None

    analysis = SessionAnalysis(
        session_id=session_id,
        project_slug=project_slug,
        transcript_path=str(path),
        source="cursor",
        user_turns=0,
        assistant_messages=0,
        tool_calls=0,
    )

    naive_cumulative = 0
    prev_naive = 0
    prev_synth = 0
    rolling_pairs: list[tuple[int, int]] = []
    turn_idx = 0
    i = 0

    while i < len(lines):
        record = lines[i]
        if record.get("role") != "user":
            i += 1
            continue

        turn_idx += 1
        analysis.user_turns += 1
        user_blocks = blocks_from_record(record)
        user_chars = sum(len(b.text) for b in user_blocks)
        for p in paths_from_text("".join(b.text for b in user_blocks)):
            analysis.unique_files.add(p)

        assistant_chars = 0
        tool_calls = 0
        turn_files: list[str] = []
        i += 1
        while i < len(lines) and lines[i].get("role") == "assistant":
            analysis.assistant_messages += 1
            for block in blocks_from_record(lines[i]):
                assistant_chars += len(block.text)
                for p in paths_from_text(block.text):
                    turn_files.append(p)
                    analysis.unique_files.add(p)
                if block.tool_name:
                    tool_calls += 1
                    analysis.tool_calls += 1
                    analysis.tool_names[block.tool_name] += 1
                    for p in paths_from_tool_input(block.tool_input):
                        turn_files.append(p)
                        analysis.unique_files.add(p)
                        analysis.file_touches.append(
                            FileTouch(path=p, turn=turn_idx, tool=block.tool_name or "unknown")
                        )
            i += 1

        naive_cumulative += user_chars + assistant_chars
        rolling_pairs.append((user_chars, assistant_chars))
        if len(rolling_pairs) > max_turns_threshold:
            rolling_pairs = rolling_pairs[-max_turns_threshold:]

        layer3_chars = sum(u + a for u, a in rolling_pairs)
        synth_chars = layer1_chars + ledger_chars + layer3_chars + user_chars

        analysis.turns.append(
            TurnSnapshot(
                turn=turn_idx,
                user_chars=user_chars,
                assistant_chars=assistant_chars,
                tool_calls=tool_calls,
                files_touched=sorted(set(turn_files)),
                naive_cumulative_chars=naive_cumulative,
                synthesizer_est_chars=synth_chars,
                layer3_est_chars=layer3_chars,
                compaction_would_fire=turn_idx % max_turns_threshold == 0,
                naive_delta_chars=naive_cumulative - prev_naive,
                synth_delta_chars=synth_chars - prev_synth,
            )
        )
        prev_naive = naive_cumulative
        prev_synth = synth_chars

    return analysis if analysis.user_turns else None
