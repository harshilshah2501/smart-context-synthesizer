#!/usr/bin/env python3
"""
Deep-dive analysis of one long IDE session for smart-synthesizer R&D.

Supports:
  --source cursor   ~/.cursor/projects/.../agent-transcripts/
  --source claude   ~/.claude/projects/.../*.jsonl  (Max subscription, no API key)

Usage:
    .venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --largest
    .venv/bin/python context-synthesizer/analyze_hot_session.py --source cursor --project m-coder --largest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import claude_parse as claude_mod
import cursor_parse as cursor_mod
from session_models import SessionAnalysis, TurnSnapshot
from telemetry import estimate_tokens

DEFAULT_CURSOR_ROOT = Path.home() / ".cursor" / "projects"
SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[float], width: int = 48) -> str:
    if not values:
        return ""
    if len(values) <= width:
        sampled = values
    else:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    lo, hi = min(sampled), max(sampled)
    if hi <= lo:
        return SPARK_BLOCKS[0] * len(sampled)
    return "".join(SPARK_BLOCKS[int((v - lo) / (hi - lo) * (len(SPARK_BLOCKS) - 1))] for v in sampled)


def _bar(ratio: float, width: int = 24) -> str:
    ratio = max(0.0, min(1.0, ratio))
    return "█" * int(ratio * width) + "░" * (width - int(ratio * width))


def file_reread_report(analysis: SessionAnalysis, *, top_n: int = 15) -> list[dict]:
    read_tools = cursor_mod.READ_TOOLS | claude_mod.READ_TOOLS
    by_path: dict[str, list[int]] = defaultdict(list)
    for touch in analysis.file_touches:
        if touch.tool in read_tools:
            by_path[touch.path].append(touch.turn)

    rows: list[dict] = []
    for path, turns in by_path.items():
        if len(turns) < 2:
            continue
        gaps = [turns[i] - turns[i - 1] for i in range(1, len(turns))]
        rows.append({
            "path": path,
            "reads": len(turns),
            "first_turn": turns[0],
            "last_turn": turns[-1],
            "avg_gap": sum(gaps) / len(gaps) if gaps else 0,
            "turns": turns[:20],
        })
    rows.sort(key=lambda r: (-r["reads"], -r["last_turn"]))
    return rows[:top_n]


def growth_spikes(analysis: SessionAnalysis, *, top_n: int = 10) -> list[TurnSnapshot]:
    return sorted(analysis.turns, key=lambda t: t.naive_delta_chars, reverse=True)[:top_n]


def compaction_turns(analysis: SessionAnalysis) -> list[TurnSnapshot]:
    return [t for t in analysis.turns if t.compaction_would_fire]


def synthesizer_recommendations(
    analysis: SessionAnalysis,
    rereads: list[dict],
    spikes: list[TurnSnapshot],
) -> list[str]:
    recs: list[str] = []
    if analysis.user_turns >= 50:
        recs.append(
            f"Session has {analysis.user_turns} turns — use token-based compaction trigger, not turn-count only"
        )
    if getattr(analysis, "auto_compactions", 0) > 0:
        recs.append(
            f"Claude auto-compacted {analysis.auto_compactions}x — compare with synthesizer ledger quality"
        )
    if rereads and rereads[0]["reads"] >= 10:
        recs.append(
            f"Ledger: keep latest state of {Path(rereads[0]['path']).name} only — {rereads[0]['reads']} reads"
        )
    for tool, threshold, msg in [
        ("Shell", 200, "Collapse Shell output in ledger"),
        ("Bash", 200, "Collapse Bash output in ledger"),
    ]:
        n = analysis.tool_names.get(tool, 0)
        if n >= threshold:
            recs.append(f"{msg} — {n:,} calls")
    read_n = sum(analysis.tool_names.get(t, 0) for t in ("Read", "ReadFile"))
    if read_n > 200:
        recs.append(f"Dedupe Read snippets — {read_n:,} read operations")
    if spikes and spikes[0].naive_delta_chars > 50_000:
        recs.append(
            f"Spike at turn {spikes[0].turn} (+{estimate_tokens(spikes[0].naive_delta_chars):,} tok) — dump compaction"
        )
    if analysis.source == "claude-cli" and analysis.total_input_tokens:
        cache_pct = analysis.total_cache_read / analysis.total_input_tokens * 100
        if cache_pct < 30:
            recs.append(f"Low cache read ({cache_pct:.0f}%) — production Claude.md + synthesizer would help")
    if not recs:
        recs.append("Review top re-reads and spike turns for ledger prompt tuning")
    return recs[:6]


def print_report(analysis: SessionAnalysis) -> None:
    rereads = file_reread_report(analysis)
    spikes = growth_spikes(analysis)
    compactions = compaction_turns(analysis)
    naive_series = [float(t.naive_cumulative_chars) for t in analysis.turns]
    synth_series = [float(t.synthesizer_est_chars) for t in analysis.turns]
    source_label = "Claude CLI (Max)" if analysis.source == "claude-cli" else "Cursor IDE"

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║              HOT SESSION — SMART SYNTHESIZER ANALYSIS                ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Source:     {source_label:<58} ║")
    print(f"║ Session:    {analysis.session_id[:58]:<58} ║")
    print(f"║ Project:    {analysis.project_slug[:58]:<58} ║")
    print(f"║ Path:       {analysis.transcript_path[-58:]:<58} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ User turns:           {analysis.user_turns:>8,}{' ' * 39}║")
    print(f"║ Assistant messages:   {analysis.assistant_messages:>8,}{' ' * 39}║")
    print(f"║ Tool calls:           {analysis.tool_calls:>8,}{' ' * 39}║")
    print(f"║ Unique file paths:    {len(analysis.unique_files):>8,}{' ' * 39}║")
    if analysis.source == "claude-cli" and analysis.total_input_tokens:
        out_tok = sum(t.output_tokens for t in analysis.turns)
        cache_pct = analysis.total_cache_read / analysis.total_input_tokens * 100
        print(f"║ Real input tokens:     {analysis.total_input_tokens:>8,}  (from CLI logs){' ' * 15}║")
        print(f"║ Real cache read:       {analysis.total_cache_read:>8,}  ({cache_pct:.1f}%){' ' * 22}║")
        print(f"║ Real output tokens:    {out_tok:>8,}{' ' * 39}║")
        if analysis.auto_compactions:
            print(f"║ Claude auto-compact:   {analysis.auto_compactions:>8,}{' ' * 39}║")
    print(f"║ Final naive est:      {estimate_tokens(analysis.final_naive_chars):>8,} tokens{' ' * 28}║")
    print(f"║ Final synth est:      {estimate_tokens(analysis.final_synth_chars):>8,} tokens{' ' * 28}║")
    print(f"║ Compression est:      {analysis.compression_ratio * 100:>7.1f}%{' ' * 39}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ CONTEXT GROWTH (sparklines)                                          ║")
    print(f"║ naive: {_sparkline(naive_series):<58} ║")
    print(f"║ synth: {_sparkline(synth_series):<58} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ COMPACTION TRIGGERS (synthesizer @ MAX_TURNS_THRESHOLD)              ║")
    for t in compactions[:12]:
        extra = " auto" if t.auto_compact else ""
        print(
            f"║ {t.turn:4d}   naive {estimate_tokens(t.naive_cumulative_chars):>8,} "
            f"synth {estimate_tokens(t.synthesizer_est_chars):>7,}  tools {t.tool_calls:>4}{extra:<6} ║"
        )
    if len(compactions) > 12:
        print(f"║ ... {len(compactions) - 12} more{' ' * 52}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ TOP GROWTH SPIKES                                                    ║")
    for t in spikes[:8]:
        print(
            f"║ turn {t.turn:4d}  +{estimate_tokens(t.naive_delta_chars):>7,} tok  "
            f"tools {t.tool_calls:>4}  user {t.user_chars:>6}  asst {t.assistant_chars:>7} ║"
        )
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ TOP FILE RE-READS                                                    ║")
    for row in rereads[:10]:
        short = row["path"] if len(row["path"]) <= 58 else "…" + row["path"][-57:]
        print(f"║ {row['reads']:4d}   {short:<58} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ TOOL MIX                                                             ║")
    total_tools = sum(analysis.tool_names.values()) or 1
    for name, cnt in analysis.tool_names.most_common(8):
        print(f"║ {name:<16} {_bar(cnt / total_tools):>24} {cnt:>6,} ({cnt/total_tools*100:4.1f}%) ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ RECOMMENDATIONS                                                      ║")
    for rec in synthesizer_recommendations(analysis, rereads, spikes):
        print(f"║ • {rec[:68]:<68} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")


def build_export(analysis: SessionAnalysis) -> dict:
    rereads = file_reread_report(analysis, top_n=25)
    spikes = growth_spikes(analysis, top_n=20)
    return {
        "source": analysis.source,
        "session_id": analysis.session_id,
        "project_slug": analysis.project_slug,
        "transcript_path": analysis.transcript_path,
        "user_turns": analysis.user_turns,
        "tool_calls": analysis.tool_calls,
        "total_input_tokens": analysis.total_input_tokens,
        "total_cache_read": analysis.total_cache_read,
        "auto_compactions": analysis.auto_compactions,
        "compression_ratio_est": round(analysis.compression_ratio, 4),
        "file_rereads": rereads,
        "growth_spikes": [{"turn": t.turn, "naive_delta_tokens_est": estimate_tokens(t.naive_delta_chars)} for t in spikes],
        "turn_series": [
            {
                "turn": t.turn,
                "naive_cumulative_chars": t.naive_cumulative_chars,
                "synthesizer_est_chars": t.synthesizer_est_chars,
                "input_tokens": t.input_tokens,
                "cache_read_tokens": t.cache_read_tokens,
                "compaction_would_fire": t.compaction_would_fire,
                "auto_compact": t.auto_compact,
            }
            for t in analysis.turns
        ],
        "recommendations": synthesizer_recommendations(analysis, rereads, spikes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deep-dive one session for synthesizer tuning.")
    parser.add_argument("--source", choices=["cursor", "claude"], default="claude",
                        help="cursor=~/.cursor/projects, claude=~/.claude/projects (default)")
    parser.add_argument("--cursor-root", type=Path, default=DEFAULT_CURSOR_ROOT)
    parser.add_argument("--cli-root", type=Path, default=claude_mod.DEFAULT_CLI_ROOT)
    parser.add_argument("--project", help="Project path substring filter")
    parser.add_argument("--session", help="Session UUID or prefix")
    parser.add_argument("--largest", action="store_true", help="Pick largest transcript")
    parser.add_argument("--layer1-chars", type=int, default=0)
    parser.add_argument("--ledger-chars", type=int, default=2000)
    parser.add_argument("--max-turns", type=int, default=int(os.environ.get("MAX_TURNS_THRESHOLD", "10")))
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()

    layer1 = args.layer1_chars
    if layer1 <= 0:
        claude_md = Path(__file__).resolve().parent / "Claude.md"
        layer1 = len(claude_md.read_text(encoding="utf-8")) if claude_md.is_file() else 0

    if args.source == "claude":
        root = args.cli_root
        find_fn = claude_mod.find_transcript
        analyze_fn = claude_mod.analyze_transcript
    else:
        root = args.cursor_root
        find_fn = cursor_mod.find_transcript
        analyze_fn = cursor_mod.analyze_transcript

    path = find_fn(
        root,
        session_id=args.session,
        project=args.project,
        pick_largest=args.largest or not args.session,
    )
    if not path:
        print(f"ERROR: No {args.source} session found under {root}", file=sys.stderr)
        return 1

    analysis = analyze_fn(
        path,
        layer1_chars=layer1,
        ledger_chars=args.ledger_chars,
        max_turns_threshold=args.max_turns,
    )
    if not analysis:
        print(f"ERROR: Could not parse {path}", file=sys.stderr)
        return 1

    print_report(analysis)
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(json.dumps(build_export(analysis), indent=2), encoding="utf-8")
        print(f"\nExported → {args.export}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
