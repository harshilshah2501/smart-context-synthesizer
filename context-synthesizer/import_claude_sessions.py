#!/usr/bin/env python3
"""
Import Claude Code CLI sessions for synthesizer R&D (Mode D — Max subscription).

No API key or proxy required. Reads local logs from:
  ~/.claude/projects/<project>/<session-id>.jsonl

Claude Max / Pro developers use Claude Code normally; run this weekly to export
corpus stats + real token usage for team aggregation.

Usage:
    .venv/bin/python context-synthesizer/import_claude_sessions.py
    .venv/bin/python context-synthesizer/import_claude_sessions.py --min-turns 25
    .venv/bin/python context-synthesizer/import_claude_sessions.py --export team.csv
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import sys
from pathlib import Path

from claude_parse import DEFAULT_CLI_ROOT, analyze_transcript, find_transcripts
from session_models import SessionAnalysis
from telemetry import compute_costs, estimate_tokens, UsageSnapshot, utc_now_iso

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "stats" / "claude_corpus.jsonl"


def session_to_event(analysis: SessionAnalysis, *, developer_id: str) -> dict:
    last = analysis.turns[-1] if analysis.turns else None
    total_usage = UsageSnapshot(
        input_tokens=last.input_tokens if last else 0,
        cache_read_input_tokens=last.cache_read_tokens if last else 0,
        cache_creation_input_tokens=last.cache_write_tokens if last else 0,
        output_tokens=last.output_tokens if last else 0,
    )
    cost = compute_costs(total_usage) if total_usage.total_input_tokens else None
    return {
        "ts": utc_now_iso(),
        "source": "claude_corpus",
        "developer_id": developer_id,
        "session_id": analysis.session_id,
        "project_path": analysis.project_slug,
        "client": "claude-cli",
        "turn_number": analysis.user_turns,
        "usage": {
            "input_tokens": total_usage.input_tokens,
            "cache_read_input_tokens": total_usage.cache_read_input_tokens,
            "cache_creation_input_tokens": total_usage.cache_creation_input_tokens,
            "output_tokens": total_usage.output_tokens,
        },
        "cost": {
            "actual_usd": cost.actual_usd,
            "baseline_usd": cost.baseline_usd,
            "saved_usd": cost.saved_usd,
            "savings_pct": cost.savings_pct,
            "cache_efficiency_pct": cost.cache_efficiency_pct,
        } if cost else {},
        "extra": {
            "transcript_path": analysis.transcript_path,
            "assistant_messages": analysis.assistant_messages,
            "tool_calls": analysis.tool_calls,
            "unique_files": len(analysis.unique_files),
            "auto_compactions": analysis.auto_compactions,
            "top_tools": dict(analysis.tool_names.most_common(8)),
            "final_naive_chars": analysis.final_naive_chars,
            "final_synth_est_chars": analysis.final_synth_chars,
            "est_naive_tokens": estimate_tokens(analysis.final_naive_chars),
            "est_synth_tokens": estimate_tokens(analysis.final_synth_chars),
            "compression_ratio_est": round(analysis.compression_ratio, 4),
            "turn_growth": [
                {
                    "turn": t.turn,
                    "naive_chars": t.naive_cumulative_chars,
                    "synth_est_chars": t.synthesizer_est_chars,
                    "input_tokens": t.input_tokens,
                    "cache_read_tokens": t.cache_read_tokens,
                    "compaction_would_fire": t.compaction_would_fire,
                    "auto_compact": t.auto_compact,
                }
                for t in analysis.turns
            ],
        },
    }


def print_report(analyses: list[SessionAnalysis], *, min_turns: int) -> None:
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║        CLAUDE CLI CORPUS — Max/Pro subscription (no API key)         ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Sessions scanned:     {len(analyses):>8}{' ' * 39}║")
    print(f"║ Sessions ≥ {min_turns} turns:   {sum(1 for a in analyses if a.user_turns >= min_turns):>8}{' ' * 39}║")
    if not analyses:
        print("║ Run Claude Code once to create ~/.claude/projects/                   ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        return

    has_usage = sum(1 for a in analyses if a.total_input_tokens > 0)
    print(f"║ With token usage:     {has_usage:>8}{' ' * 39}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ Session (turns)     real tok   synth est  save%   tools  cache%     ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    for a in sorted(analyses, key=lambda x: -x.user_turns)[:20]:
        real_t = a.total_input_tokens + a.total_output_tokens
        synth_t = estimate_tokens(a.final_synth_chars)
        save = a.compression_ratio * 100
        cache_pct = (a.total_cache_read / a.total_input_tokens * 100) if a.total_input_tokens else 0
        label = f"{a.session_id[:8]}… ({a.user_turns})"
        print(
            f"║ {label:<19} {real_t:>9,} {synth_t:>9,} {save:>6.1f}% {a.tool_calls:>6} {cache_pct:>5.1f}% ║"
        )
    if len(analyses) > 20:
        print(f"║ ... {len(analyses) - 20} more sessions{' ' * 42}║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("\nDeep-dive: analyze_hot_session.py --source claude --largest")


def export_csv(analyses: list[SessionAnalysis], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "session_id", "project_slug", "user_turns", "tool_calls", "unique_files",
        "total_input_tokens", "total_cache_read", "auto_compactions",
        "est_naive_tokens", "est_synth_tokens", "compression_ratio_est", "transcript_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for a in analyses:
            writer.writerow({
                "session_id": a.session_id,
                "project_slug": a.project_slug,
                "user_turns": a.user_turns,
                "tool_calls": a.tool_calls,
                "unique_files": len(a.unique_files),
                "total_input_tokens": a.total_input_tokens,
                "total_cache_read": a.total_cache_read,
                "auto_compactions": a.auto_compactions,
                "est_naive_tokens": estimate_tokens(a.final_naive_chars),
                "est_synth_tokens": estimate_tokens(a.final_synth_chars),
                "compression_ratio_est": round(a.compression_ratio, 4),
                "transcript_path": a.transcript_path,
            })
    print(f"Exported {len(analyses)} sessions → {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Claude CLI sessions (Max subscription, no proxy).")
    parser.add_argument("--cli-root", type=Path, default=DEFAULT_CLI_ROOT)
    parser.add_argument("--project", help="Filter by project path substring")
    parser.add_argument("--min-turns", type=int, default=1)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--developer", default=os.environ.get("TELEMETRY_DEVELOPER_ID") or getpass.getuser())
    parser.add_argument("--layer1-chars", type=int, default=0)
    parser.add_argument("--ledger-chars", type=int, default=2000)
    parser.add_argument("--max-turns", type=int, default=int(os.environ.get("MAX_TURNS_THRESHOLD", "10")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()

    layer1 = args.layer1_chars
    if layer1 <= 0:
        claude_md = Path(__file__).resolve().parent / "Claude.md"
        layer1 = len(claude_md.read_text(encoding="utf-8")) if claude_md.is_file() else 0

    if not args.cli_root.is_dir():
        print(f"ERROR: {args.cli_root} not found. Use Claude Code in a project first.", file=sys.stderr)
        return 1

    transcripts = find_transcripts(args.cli_root, project_filter=args.project)
    if not transcripts:
        print(f"No sessions under {args.cli_root}", file=sys.stderr)
        return 1

    analyses: list[SessionAnalysis] = []
    for path in transcripts:
        result = analyze_transcript(
            path,
            layer1_chars=layer1,
            ledger_chars=args.ledger_chars,
            max_turns_threshold=args.max_turns,
        )
        if result and result.user_turns >= args.min_turns:
            analyses.append(result)

    print_report(analyses, min_turns=args.min_turns)

    if args.dry_run:
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("", encoding="utf-8")
    for analysis in analyses:
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(session_to_event(analysis, developer_id=args.developer), ensure_ascii=False) + "\n")
    print(f"\nWrote {len(analyses)} sessions → {args.output}")

    if args.export:
        export_csv(analyses, args.export)
    return 0


if __name__ == "__main__":
    sys.exit(main())
