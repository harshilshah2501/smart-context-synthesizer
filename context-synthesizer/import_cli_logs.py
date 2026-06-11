#!/usr/bin/env python3
"""
Import token bifurcation stats from Claude Code CLI session logs (~/.claude/projects).

Mode A — import native Claude Code session logs (~/.claude/projects) with per-turn
token bifurcation. No proxy, no API key.

Usage:
    .venv/bin/python context-synthesizer/import_cli_logs.py
    .venv/bin/python context-synthesizer/import_cli_logs.py --developer alice
    .venv/bin/python context-synthesizer/import_cli_logs.py --since 2026-06-01
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from telemetry import (
    TELEMETRY_LOG_PATH,
    CostSnapshot,
    TelemetryEvent,
    UsageSnapshot,
    append_event,
    compute_costs,
    utc_now_iso,
)

DEFAULT_CLI_ROOT = Path.home() / ".claude" / "projects"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _developer_from_path(project_dir: Path) -> str:
    """Infer developer from path or env — override with --developer."""
    return os.environ.get("TELEMETRY_DEVELOPER_ID") or getpass.getuser()


def _extract_assistant_events(
    jsonl_path: Path,
    *,
    developer_id: str,
    since: datetime | None,
) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    session_id = jsonl_path.stem
    # project path hint from parent dir name (url-encoded cwd)
    project_path = jsonl_path.parent.name

    try:
        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"WARN: skip {jsonl_path}: {exc}", file=sys.stderr)
        return events

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if record.get("type") != "assistant":
            continue

        ts_str = record.get("timestamp")
        ts = _parse_ts(ts_str)
        if since and ts and ts < since:
            continue

        message = record.get("message") or {}
        usage_raw = message.get("usage")
        if not usage_raw:
            continue

        usage = UsageSnapshot.from_api(usage_raw)
        if usage.total_input_tokens == 0 and usage.output_tokens == 0:
            continue

        cost = compute_costs(usage)
        model = message.get("model") or "unknown"

        events.append(
            TelemetryEvent(
                ts=ts_str or utc_now_iso(),
                source="cli_import",
                developer_id=developer_id,
                session_id=record.get("sessionId") or session_id,
                model=model,
                latency_s=None,
                usage=usage,
                cost=cost,
                project_path=project_path,
                client="claude-cli",
                extra={"log_file": str(jsonl_path)},
            )
        )
    return events


def import_logs(
    *,
    cli_root: Path,
    developer_id: str | None,
    since: datetime | None,
    output: Path,
    dry_run: bool,
) -> int:
    if not cli_root.is_dir():
        print(f"ERROR: Claude CLI log directory not found: {cli_root}", file=sys.stderr)
        print("Developers must run Claude Code at least once to create ~/.claude/projects/", file=sys.stderr)
        return 1

    jsonl_files = sorted(cli_root.glob("**/*.jsonl"))
    if not jsonl_files:
        print(f"No .jsonl session files under {cli_root}", file=sys.stderr)
        return 1

    dev = developer_id or _developer_from_path(cli_root)
    total_events = 0
    agg_usage = UsageSnapshot()

    for path in jsonl_files:
        for event in _extract_assistant_events(path, developer_id=dev, since=since):
            total_events += 1
            agg_usage.input_tokens += event.usage.input_tokens
            agg_usage.cache_read_input_tokens += event.usage.cache_read_input_tokens
            agg_usage.cache_creation_input_tokens += event.usage.cache_creation_input_tokens
            agg_usage.output_tokens += event.usage.output_tokens
            if not dry_run:
                append_event(event, output)

    if total_events == 0:
        print("No assistant usage records found.", file=sys.stderr)
        return 1

    agg_cost = compute_costs(agg_usage)
    print(f"Imported {total_events} assistant turns from {len(jsonl_files)} session file(s)")
    print(f"Developer: {dev}")
    print(f"Output:    {output}" + (" (dry run)" if dry_run else ""))
    print(f"Uncached:  {agg_usage.input_tokens:,} | Cache read: {agg_usage.cache_read_input_tokens:,} | "
          f"Cache write: {agg_usage.cache_creation_input_tokens:,} | Output: {agg_usage.output_tokens:,}")
    print(f"Baseline:  ${agg_cost.baseline_usd:.4f} | Actual: ${agg_cost.actual_usd:.4f} | "
          f"Saved: ${agg_cost.saved_usd:.4f} ({agg_cost.savings_pct:.1f}%)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Claude Code CLI logs into telemetry JSONL.")
    parser.add_argument(
        "--cli-root",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CLI_LOG_ROOT", str(DEFAULT_CLI_ROOT))),
        help="Root of Claude Code project logs (default: ~/.claude/projects)",
    )
    parser.add_argument(
        "--developer",
        default=os.environ.get("TELEMETRY_DEVELOPER_ID"),
        help="Developer id for imported events (default: $TELEMETRY_DEVELOPER_ID or OS username)",
    )
    parser.add_argument("--since", help="Only import records on/after YYYY-MM-DD")
    parser.add_argument(
        "--output",
        type=Path,
        default=TELEMETRY_LOG_PATH,
        help="Telemetry JSONL output path",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and summarize without writing")
    args = parser.parse_args()

    since_dt = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=datetime.now().astimezone().tzinfo)

    return import_logs(
        cli_root=args.cli_root,
        developer_id=args.developer,
        since=since_dt,
        output=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
