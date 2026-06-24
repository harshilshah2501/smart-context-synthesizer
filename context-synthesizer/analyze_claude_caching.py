#!/usr/bin/env python3
"""Analyze native Claude Code caching behaviour from session JSONL logs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from claude_parse import is_human_user, usage_from_assistant


def analyze_session(path: Path) -> dict | None:
    try:
        lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    except (OSError, json.JSONDecodeError):
        return None

    models: set[str] = set()
    assistant_msgs = 0
    msgs_cache_read = 0
    msgs_cache_write = 0
    msgs_uncached_only = 0
    compact_events = 0
    turns: list[dict] = []

    turn_n = 0
    i = 0
    while i < len(lines):
        rec = lines[i]
        if rec.get("type") == "system" and rec.get("subtype") == "compact_boundary":
            compact_events += 1
            i += 1
            continue

        if not is_human_user(rec):
            if rec.get("type") == "assistant":
                assistant_msgs += 1
                u = usage_from_assistant(rec)
                cr, cw = u["cache_read_input_tokens"], u["cache_creation_input_tokens"]
                if cr > 0:
                    msgs_cache_read += 1
                if cw > 0:
                    msgs_cache_write += 1
                if cr == 0 and cw == 0:
                    msgs_uncached_only += 1
                m = (rec.get("message") or {}).get("model")
                if m:
                    models.add(m)
            i += 1
            continue

        turn_n += 1
        turn_u = {"input_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "output_tokens": 0}
        turn_had_compact = False
        i += 1
        while i < len(lines):
            rec = lines[i]
            if rec.get("type") == "system" and rec.get("subtype") == "compact_boundary":
                turn_had_compact = True
                compact_events += 1
                i += 1
                continue
            if is_human_user(rec):
                break
            if rec.get("type") == "assistant":
                assistant_msgs += 1
                u = usage_from_assistant(rec)
                cr, cw = u["cache_read_input_tokens"], u["cache_creation_input_tokens"]
                if cr > 0:
                    msgs_cache_read += 1
                if cw > 0:
                    msgs_cache_write += 1
                if cr == 0 and cw == 0:
                    msgs_uncached_only += 1
                for k in turn_u:
                    turn_u[k] = max(turn_u[k], u.get(k, 0))
                m = (rec.get("message") or {}).get("model")
                if m:
                    models.add(m)
            i += 1

        total_in = turn_u["input_tokens"] + turn_u["cache_read_input_tokens"] + turn_u["cache_creation_input_tokens"]
        turns.append({
            "turn": turn_n,
            **turn_u,
            "total_in": total_in,
            "cache_read_pct": (turn_u["cache_read_input_tokens"] / total_in * 100) if total_in else 0,
            "had_compact_boundary": turn_had_compact,
        })

    if not turns:
        return None

    turns_with_read = sum(1 for t in turns if t["cache_read_input_tokens"] > 0)
    turns_with_write = sum(1 for t in turns if t["cache_creation_input_tokens"] > 0)
    turns_no_cache = sum(1 for t in turns if t["cache_read_input_tokens"] == 0 and t["cache_creation_input_tokens"] == 0)

    return {
        "session_id": path.stem,
        "path": str(path),
        "user_turns": turn_n,
        "assistant_msgs": assistant_msgs,
        "models": sorted(models),
        "compact_boundaries": compact_events,
        "turns": turns,
        "turns_with_cache_read": turns_with_read,
        "turns_with_cache_write": turns_with_write,
        "turns_no_cache_signal": turns_no_cache,
        "pct_turns_cache_read": turns_with_read / turn_n * 100 if turn_n else 0,
        "msgs_cache_read": msgs_cache_read,
        "msgs_cache_write": msgs_cache_write,
        "msgs_uncached_only": msgs_uncached_only,
        "pct_msgs_cache_read": msgs_cache_read / assistant_msgs * 100 if assistant_msgs else 0,
    }


def print_report(sessions: list[dict]) -> None:
    total_turns = sum(s["user_turns"] for s in sessions)
    total_msgs = sum(s["assistant_msgs"] for s in sessions)
    turns_read = sum(s["turns_with_cache_read"] for s in sessions)
    turns_write = sum(s["turns_with_cache_write"] for s in sessions)
    turns_none = sum(s["turns_no_cache_signal"] for s in sessions)
    msgs_read = sum(s["msgs_cache_read"] for s in sessions)
    msgs_write = sum(s["msgs_cache_write"] for s in sessions)
    msgs_none = sum(s["msgs_uncached_only"] for s in sessions)

    all_models = sorted({m for s in sessions for m in s["models"]})

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║     NATIVE CLAUDE CODE CACHING — developer-a session logs            ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Sessions:              {len(sessions):>6}{' ' * 39}║")
    print(f"║ User turns:            {total_turns:>6}{' ' * 39}║")
    print(f"║ Assistant API msgs:    {total_msgs:>6}{' ' * 39}║")
    print(f"║ Models seen:           {', '.join(all_models)[:52]:<52} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ PER USER TURN (end-of-turn cumulative usage snapshot)                ║")
    print(f"║ Turns with cache_read > 0:     {turns_read:>6} / {total_turns:<6} ({turns_read/total_turns*100:>5.1f}%){' ' * 12}║")
    print(f"║ Turns with cache_write > 0:    {turns_write:>6} / {total_turns:<6} ({turns_write/total_turns*100:>5.1f}%){' ' * 12}║")
    print(f"║ Turns with NO cache signal:     {turns_none:>6} / {total_turns:<6} ({turns_none/total_turns*100:>5.1f}%){' ' * 12}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ PER ASSISTANT MESSAGE (each API response in logs)                    ║")
    print(f"║ Msgs with cache_read > 0:      {msgs_read:>6} / {total_msgs:<6} ({msgs_read/total_msgs*100:>5.1f}%){' ' * 12}║")
    print(f"║ Msgs with cache_write > 0:     {msgs_write:>6} / {total_msgs:<6} ({msgs_write/total_msgs*100:>5.1f}%){' ' * 12}║")
    print(f"║ Msgs uncached-only (no r/w):   {msgs_none:>6} / {total_msgs:<6} ({msgs_none/total_msgs*100:>5.1f}%){' ' * 12}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ INTERPRETATION                                                       ║")
    print("║ • cache_read > 0  → prefix was served from Anthropic prompt cache    ║")
    print("║ • cache_write > 0 → prefix was written to cache (cold / bust / new)  ║")
    print("║ • Claude Code does NOT expose cache_control in logs — usage only     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    print("\nPer-session breakdown (turns with cache_read %):")
    print(f"{'session':<10} {'turns':>6} {'read%':>7} {'write turns':>12} {'no cache':>9} {'compact':>8} model")
    for s in sorted(sessions, key=lambda x: -x["user_turns"])[:15]:
        model = s["models"][0][:20] if s["models"] else "?"
        print(
            f"{s['session_id'][:8]:<10} {s['user_turns']:>6} {s['pct_turns_cache_read']:>6.1f}% "
            f"{s['turns_with_cache_write']:>12} {s['turns_no_cache_signal']:>9} {s['compact_boundaries']:>8} {model}"
        )

    # Hot session turn-by-turn pattern for largest
    hot = max(sessions, key=lambda x: x["user_turns"])
    turns = hot["turns"]
    print(f"\nHot session {hot['session_id'][:8]} — first 15 turns:")
    print(f"{'turn':>5} {'cache_read':>12} {'cache_write':>12} {'uncached':>10} {'read%':>7} compact")
    for t in turns[:15]:
        print(
            f"{t['turn']:>5} {t['cache_read_input_tokens']:>12,} {t['cache_creation_input_tokens']:>12,} "
            f"{t['input_tokens']:>10,} {t['cache_read_pct']:>6.1f}% {'yes' if t['had_compact_boundary'] else ''}"
        )
    print(f"\n... turn {turns[-1]['turn']}: cache_read={turns[-1]['cache_read_input_tokens']:,} "
          f"({turns[-1]['cache_read_pct']:.1f}% of input)")

    # Write turn pattern: which turns get cache_write
    write_turns = [t["turn"] for t in turns if t["cache_creation_input_tokens"] > 0]
    print(f"\nHot session cache_write turns (first 20): {write_turns[:20]}")
    if len(write_turns) > 20:
        print(f"  ... total {len(write_turns)} turns with cache_write")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli-root", type=Path, required=True)
    args = parser.parse_args()

    sessions = []
    for path in sorted(args.cli_root.glob("**/*.jsonl")):
        if "subagents" in path.parts:
            continue
        r = analyze_session(path)
        if r:
            sessions.append(r)

    if not sessions:
        print("No sessions found", file=sys.stderr)
        return 1

    print_report(sessions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
