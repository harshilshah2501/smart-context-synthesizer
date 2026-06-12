#!/usr/bin/env python3
"""One-page weekly summary for developers (uploaded to shared drive)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def _cache_pct(row: dict) -> str:
    try:
        inp = float(row.get("total_input_tokens") or 0)
        read = float(row.get("total_cache_read") or 0)
        if inp <= 0:
            return "—"
        return f"{read / inp * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def pct(value: str | float | None) -> str:
    if value is None or value == "":
        return "—"
    try:
        v = float(value)
        if v < 0:
            return f"{v * 100:.1f}% (short session — overhead)"
        return f"{v * 100:.1f}%"
    except ValueError:
        return str(value)


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "Usage: generate_weekly_summary.py <corpus.csv> <developer> <week> <out.md>",
            file=sys.stderr,
        )
        return 1

    csv_path = Path(sys.argv[1])
    developer = sys.argv[2]
    week = sys.argv[3]
    out_path = Path(sys.argv[4])

    if not csv_path.is_file():
        out_path.write_text(
            f"# Weekly summary — {developer} ({week})\n\nNo sessions exported.\n",
            encoding="utf-8",
        )
        return 0

    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        out_path.write_text(
            f"# Weekly summary — {developer} ({week})\n\nNo sessions matched export filters.\n",
            encoding="utf-8",
        )
        return 0

    def turns(row: dict) -> int:
        try:
            return int(row.get("user_turns") or 0)
        except ValueError:
            return 0

    longest = max(rows, key=turns)
    with_usage = [r for r in rows if (r.get("total_input_tokens") or "0") not in ("", "0")]
    avg_comp = 0.0
    comp_rows = [r for r in rows if r.get("compression_ratio_est")]
    if comp_rows:
        avg_comp = sum(float(r["compression_ratio_est"]) for r in comp_rows) / len(comp_rows)

    lines = [
        f"# Weekly context summary — {developer}",
        f"",
        f"**Week ending:** {week}  ",
        f"**Sessions exported:** {len(rows)}  ",
        f"**Sessions with token usage:** {len(with_usage)}",
        f"",
        f"## Longest session this week",
        f"",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Session | `{longest.get('session_id', '')[:8]}…` |",
        f"| User turns | {longest.get('user_turns', '—')} |",
        f"| Tool calls | {longest.get('tool_calls', '—')} |",
        f"| Est. naive context | {longest.get('est_naive_tokens', '—')} tokens |",
        f"| Est. synthesizer context | {longest.get('est_synth_tokens', '—')} tokens |",
        f"| **Compression estimate** | **{pct(longest.get('compression_ratio_est'))}** |",
        f"| Cache read (last turn) | {_cache_pct(longest)} |",
        f"",
        f"## What this means",
        f"",
        f"- **If you use the local proxy** (`setup_developer.sh --enable-proxy`): Claude Code routes through the synthesizer automatically — long sessions stay bounded instead of growing unbounded history.",
        f"- **This report** shows how much smaller a synthesizer-shaped payload would be vs keeping the full transcript (counterfactual).",
        f"- Corpus average compression (all sessions): **{pct(avg_comp)}**.",
        f"",
        f"## Team",
        f"",
        f"Raw data: `{week}_{developer}_claude.jsonl` on the shared drive. Team lead uses this to tune compaction rules.",
        f"",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
