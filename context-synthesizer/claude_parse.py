"""Parse Claude Code CLI session logs (~/.claude/projects) for corpus analysis."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from session_models import FileTouch, SessionAnalysis, TurnSnapshot

PATH_RE = re.compile(r"(?:/[\w.\-]+)+(?:/[\w.\-]+)*")
READ_TOOLS = frozenset({
    "Read", "ReadFile", "Grep", "rg", "Glob", "SemanticSearch", "Bash", "LS",
})
DEFAULT_CLI_ROOT = Path.home() / ".claude" / "projects"


def decode_project_slug(dir_name: str) -> str:
    """Claude encodes cwd as dir name, often with hyphens for slashes."""
    if dir_name.startswith("-") or "-" in dir_name:
        return unquote(dir_name.replace("-", "/").lstrip("/"))
    return dir_name


def is_human_user(record: dict) -> bool:
    if record.get("type") != "user":
        return False
    if record.get("isSidechain"):
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and (block.get("text") or "").strip():
                return True
        return False
    return False


def content_chars(content: object) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    total += len(block.get("text") or "")
                elif block.get("type") == "tool_result":
                    total += len(str(block.get("content") or ""))
        return total
    return 0


def parse_assistant_blocks(record: dict) -> tuple[int, int, list[tuple[str, dict | None]], list[str]]:
    """Returns (chars, tool_count, [(tool_name, input), ...], paths)."""
    chars = 0
    tools: list[tuple[str, dict | None]] = []
    paths: list[str] = []
    for block in (record.get("message") or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            text = block.get("text") or ""
            chars += len(text)
            paths.extend(paths_from_text(text))
        elif kind == "tool_use":
            name = block.get("name") or "unknown"
            inp = block.get("input") if isinstance(block.get("input"), dict) else None
            tools.append((name, inp))
            paths.extend(paths_from_tool_input(inp))
    return chars, len(tools), tools, paths


def paths_from_tool_input(tool_input: dict | None) -> list[str]:
    if not tool_input:
        return []
    paths: list[str] = []
    for key in ("path", "file_path", "target_directory", "glob_pattern", "working_directory", "notebook_path"):
        val = tool_input.get(key)
        if isinstance(val, str) and ("/" in val or "\\" in val or val.endswith((".py", ".ts", ".md", ".json"))):
            paths.append(val)
    return paths


def paths_from_text(text: str) -> list[str]:
    return [m.group(0) for m in PATH_RE.finditer(text) if m.group(0).count("/") >= 2]


def usage_from_assistant(record: dict) -> dict[str, int]:
    usage = record.get("usage") or (record.get("message") or {}).get("usage") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
        "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def find_transcript(
    cli_root: Path,
    *,
    session_id: str | None,
    project: str | None,
    pick_largest: bool,
) -> Path | None:
    candidates: list[Path] = []
    for path in sorted(cli_root.glob("**/*.jsonl")):
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


def find_transcripts(cli_root: Path, *, project_filter: str | None) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(cli_root.glob("**/*.jsonl")):
        if "subagents" in path.parts:
            continue
        if project_filter and project_filter not in str(path):
            continue
        paths.append(path)
    return paths


def analyze_transcript(
    path: Path,
    *,
    layer1_chars: int,
    ledger_chars: int,
    max_turns_threshold: int,
) -> SessionAnalysis | None:
    project_slug = decode_project_slug(path.parent.name)
    session_id = path.stem

    try:
        lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    except (OSError, json.JSONDecodeError):
        return None

    analysis = SessionAnalysis(
        session_id=session_id,
        project_slug=project_slug,
        transcript_path=str(path),
        source="claude-cli",
        user_turns=0,
        assistant_messages=0,
        tool_calls=0,
    )

    naive_cumulative = 0
    prev_naive = 0
    prev_synth = 0
    rolling_pairs: list[tuple[int, int]] = []
    turn_idx = 0
    auto_compacts = 0

    i = 0
    while i < len(lines):
        record = lines[i]

        if record.get("type") == "system" and record.get("subtype") == "compact_boundary":
            auto_compacts += 1
            i += 1
            continue

        if not is_human_user(record):
            i += 1
            continue

        turn_idx += 1
        analysis.user_turns += 1
        user_chars = content_chars((record.get("message") or {}).get("content"))
        for p in paths_from_text(str((record.get("message") or {}).get("content", ""))):
            analysis.unique_files.add(p)

        assistant_chars = 0
        tool_calls = 0
        turn_files: list[str] = []
        # Claude CLI logs cumulative usage per assistant message — take max per turn, not sum.
        turn_usage = {"input_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 0}
        turn_auto_compact = False

        i += 1
        while i < len(lines):
            rec = lines[i]
            if rec.get("type") == "system" and rec.get("subtype") == "compact_boundary":
                turn_auto_compact = True
                auto_compacts += 1
                i += 1
                continue
            if is_human_user(rec):
                break
            if rec.get("type") == "assistant":
                analysis.assistant_messages += 1
                a_chars, n_tools, tool_list, paths = parse_assistant_blocks(rec)
                assistant_chars += a_chars
                tool_calls += n_tools
                turn_files.extend(paths)
                for name, inp in tool_list:
                    analysis.tool_calls += 1
                    analysis.tool_names[name] += 1
                    for p in paths_from_tool_input(inp):
                        turn_files.append(p)
                        analysis.unique_files.add(p)
                        analysis.file_touches.append(FileTouch(path=p, turn=turn_idx, tool=name))
                u = usage_from_assistant(rec)
                for k in turn_usage:
                    turn_usage[k] = max(turn_usage[k], u.get(k, 0))
            elif rec.get("type") == "user":
                # tool results between assistant rounds
                assistant_chars += content_chars((rec.get("message") or {}).get("content"))
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
                input_tokens=turn_usage["input_tokens"],
                cache_read_tokens=turn_usage["cache_read_input_tokens"],
                cache_write_tokens=turn_usage["cache_creation_input_tokens"],
                output_tokens=turn_usage["output_tokens"],
                auto_compact=turn_auto_compact,
            )
        )
        prev_naive = naive_cumulative
        prev_synth = synth_chars

    analysis.auto_compactions = auto_compacts
    return analysis if analysis.user_turns else None
