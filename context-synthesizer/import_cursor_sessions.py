#!/usr/bin/env python3
"""
Import Cursor agent session transcripts for synthesizer R&D (Mode C).

Usage:
    .venv/bin/python context-synthesizer/import_cursor_sessions.py
    .venv/bin/python context-synthesizer/import_cursor_sessions.py --project m-coder --min-turns 25
    .venv/bin/python context-synthesizer/import_cursor_sessions.py --export stats/corpus.csv
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import os
import sys
from pathlib import Path

from cursor_parse import SessionAnalysis, analyze_transcript
from telemetry import estimate_tokens, utc_now_iso

DEFAULT_CURSOR_ROOT = Path.home() / ".cursor" / "projects"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "stats" / "cursor_corpus.jsonl"


def find_transcripts(root: Path, *, project_filter: str | None) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(root.glob("**/agent-transcripts/**/*.jsonl")):
        if "subagents" in path.parts:
            continue
        if project_filter and project_filter not in str(path):
            continue
        paths.append(path)
    return paths


def session_to_event(analysis: SessionAnalysis, *, developer_id: str) -> dict:
    return {
        "ts": utc_now_iso(),
        "source": "cursor_import",
        "developer_id": developer_id,
        "session_id": analysis.session_id,
        "project_path": analysis.project_slug,
        "client": "cursor",
        "turn_number": analysis.user_turns,
        "extra": {
            "transcript_path": analysis.transcript_path,
            "assistant_messages": analysis.assistant_messages,
            "tool_calls": analysis.tool_calls,
            "unique_files": len(analysis.unique_files),
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
                    "layer3_chars": t.layer3_est_chars,
                    "tool_calls": t.tool_calls,
                    "files": t.files_touched[:10],
                    "compaction_would_fire": t.compaction_would_fire,
                }
                for t in analysis.turns
            ],
        },
    }


def print_report(analyses: list[SessionAnalysis], *, min_turns: int) -> None:
    long_sessions = [a for a in analyses if a.user_turns >= min_turns]
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║           CURSOR CORPUS — SYNTHESIZER R&D DATASET                    ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Sessions scanned:     {len(analyses):>8}{' ' * 39}║")
    print(f"║ Sessions ≥ {min_turns} turns:   {len(long_sessions):>8}{' ' * 39}║")
    if not analyses:
        print("║ (no transcripts found under ~/.cursor/projects/)                     ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        return

    total_tools = sum(a.tool_calls for a in analyses)
    print(f"║ Total tool calls:      {total_tools:>8}{' ' * 39}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ Session (turns)     naive tok   synth tok   save%   tools  files     ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    for a in sorted(analyses, key=lambda x: -x.user_turns):
        naive_t = estimate_tokens(a.final_naive_chars)
        synth_t = estimate_tokens(a.final_synth_chars)
        save = a.compression_ratio * 100
        label = f"{a.session_id[:8]}… ({a.user_turns})"
        print(
            f"║ {label:<19} {naive_t:>9,} {synth_t:>9,} {save:>6.1f}% {a.tool_calls:>6} {len(a.unique_files):>6} ║"
        )
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print("\nDeep-dive one session: analyze_hot_session.py --session <id> --export stats/hot.json")


def export_csv(analyses: list[SessionAnalysis], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "session_id", "project_slug", "user_turns", "assistant_messages", "tool_calls",
        "unique_files", "final_naive_chars", "final_synth_est_chars",
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
                "assistant_messages": a.assistant_messages,
                "tool_calls": a.tool_calls,
                "unique_files": len(a.unique_files),
                "final_naive_chars": a.final_naive_chars,
                "final_synth_est_chars": a.final_synth_chars,
                "est_naive_tokens": estimate_tokens(a.final_naive_chars),
                "est_synth_tokens": estimate_tokens(a.final_synth_chars),
                "compression_ratio_est": round(a.compression_ratio, 4),
                "transcript_path": a.transcript_path,
            })
    print(f"Exported {len(analyses)} sessions → {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Cursor agent transcripts for synthesizer R&D.")
    parser.add_argument("--cursor-root", type=Path, default=DEFAULT_CURSOR_ROOT)
    parser.add_argument("--project", help="Filter by project slug substring")
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

    if not args.cursor_root.is_dir():
        print(f"ERROR: Cursor projects dir not found: {args.cursor_root}", file=sys.stderr)
        return 1

    transcripts = find_transcripts(args.cursor_root, project_filter=args.project)
    if not transcripts:
        print(f"No agent-transcripts found under {args.cursor_root}", file=sys.stderr)
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
        event = session_to_event(analysis, developer_id=args.developer)
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(analyses)} sessions → {args.output}")

    if args.export:
        export_csv(analyses, args.export)
    return 0


if __name__ == "__main__":
    sys.exit(main())
