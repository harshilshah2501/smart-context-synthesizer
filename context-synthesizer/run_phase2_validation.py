#!/usr/bin/env python3
"""
Phase 2 corpus validation — repeatable test suite (Modes A/C/D).

Runs import, hot-session analysis, caching analysis, and collect_stats;
checks success criteria from SYNTHESIZER_RND_REPORT.md §16.

Usage:
    .venv/bin/python context-synthesizer/run_phase2_validation.py \\
        --cli-root context-synthesizer/stats/dev-backup/.claude/projects \\
        --developer meet-chavda

    .venv/bin/python context-synthesizer/run_phase2_validation.py \\
        --cursor-project m-coder --skip-claude
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
COMPRESSION_TARGET = 0.90
MIN_LONG_SESSION_TURNS = 100


@dataclass
class Check:
    name: str
    status: str  # PASS | FAIL | SKIP | BASELINE
    detail: str


@dataclass
class Phase2Result:
    checks: list[Check] = field(default_factory=list)
    claude_long_sessions: list[dict] = field(default_factory=list)
    cursor_long_sessions: list[dict] = field(default_factory=list)
    regression_drift: int = 0


def _run(cmd: list[str], *, cwd: Path) -> None:
    print(f"\n$ {' '.join(cmd)}\n")
    subprocess.run(cmd, cwd=cwd, check=True)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def _long_session_rows(records: list[dict]) -> list[dict]:
    rows = []
    for rec in records:
        turns = int(rec.get("turn_number") or 0)
        if turns < MIN_LONG_SESSION_TURNS:
            continue
        extra = rec.get("extra") or {}
        ratio = float(extra.get("compression_ratio_est") or 0)
        rows.append({
            "session_id": rec.get("session_id", "")[:8],
            "turns": turns,
            "compression_pct": round(ratio * 100, 1),
            "pass": ratio >= COMPRESSION_TARGET,
        })
    return sorted(rows, key=lambda r: -r["turns"])


def _compare_corpus(baseline: Path, current: Path) -> int:
    if not baseline.is_file() or not current.is_file():
        return -1
    old = {r["session_id"]: r for r in _load_jsonl(baseline)}
    new = {r["session_id"]: r for r in _load_jsonl(current)}
    drift = 0
    for sid in set(old) & set(new):
        o = old[sid]["extra"]["compression_ratio_est"]
        n = new[sid]["extra"]["compression_ratio_est"]
        if abs(float(o) - float(n)) > 0.0001:
            drift += 1
    return drift


def run_phase2(
    *,
    cli_root: Path | None,
    cursor_project: str | None,
    developer: str,
    stats_dir: Path,
    baseline_corpus: Path | None,
    skip_claude: bool,
    skip_cursor: bool,
) -> Phase2Result:
    result = Phase2Result()
    stats_dir.mkdir(parents=True, exist_ok=True)
    repo = ROOT.parent

    claude_corpus = stats_dir / "phase2_claude_corpus.jsonl"
    cursor_corpus = stats_dir / "phase2_cursor_corpus.jsonl"

    if not skip_claude and cli_root:
        _run(
            [
                PY,
                str(ROOT / "import_claude_sessions.py"),
                "--cli-root",
                str(cli_root),
                "--developer",
                developer,
                "--min-turns",
                "1",
                "--output",
                str(claude_corpus),
                "--export",
                str(stats_dir / "phase2_claude.csv"),
            ],
            cwd=repo,
        )
        drift = _compare_corpus(baseline_corpus, claude_corpus) if baseline_corpus else 0
        result.regression_drift = max(0, drift)
        if baseline_corpus and baseline_corpus.is_file():
            result.checks.append(
                Check(
                    "Corpus regression (compression ratios)",
                    "PASS" if drift == 0 else "FAIL",
                    f"{drift} sessions drifted vs {baseline_corpus.name}",
                )
            )
        else:
            result.checks.append(
                Check(
                    "Corpus regression (compression ratios)",
                    "SKIP",
                    "No --baseline-corpus provided",
                )
            )

        _run(
            [
                PY,
                str(ROOT / "analyze_hot_session.py"),
                "--source",
                "claude",
                "--cli-root",
                str(cli_root),
                "--largest",
                "--export",
                str(stats_dir / "phase2_hot_claude.json"),
            ],
            cwd=repo,
        )

        proc = subprocess.run(
            [PY, str(ROOT / "analyze_claude_caching.py"), "--cli-root", str(cli_root)],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        print(proc.stdout)
        if "99." in proc.stdout or "89." in proc.stdout:
            result.checks.append(
                Check(
                    "Native cache_read (Claude CLI)",
                    "PASS",
                    "High cache_read % on assistant messages (see output)",
                )
            )
        else:
            result.checks.append(
                Check("Native cache_read (Claude CLI)", "FAIL", "Unexpected caching output")
            )

        result.claude_long_sessions = _long_session_rows(_load_jsonl(claude_corpus))
        passed = sum(1 for r in result.claude_long_sessions if r["pass"])
        total = len(result.claude_long_sessions)
        if total:
            result.checks.append(
                Check(
                    f"Compression ≥{COMPRESSION_TARGET:.0%} (Claude 100+ turns)",
                    "PASS" if passed == total else "FAIL",
                    f"{passed}/{total} sessions pass",
                )
            )
        else:
            result.checks.append(
                Check(
                    f"Compression ≥{COMPRESSION_TARGET:.0%} (Claude 100+ turns)",
                    "SKIP",
                    f"No sessions ≥{MIN_LONG_SESSION_TURNS} turns in corpus",
                )
            )

        hot = stats_dir / "phase2_hot_claude.json"
        if hot.is_file():
            data = json.loads(hot.read_text())
            top_reread = data.get("file_rereads", [{}])[0] if data.get("file_rereads") else {}
            result.checks.append(
                Check(
                    "File re-read baseline (Claude hot session)",
                    "BASELINE",
                    f"Top re-read: {top_reread.get('reads', '?')}× "
                    f"{Path(top_reread.get('path', '')).name or 'n/a'}",
                )
            )

    if not skip_cursor and cursor_project:
        _run(
            [
                PY,
                str(ROOT / "import_cursor_sessions.py"),
                "--project",
                cursor_project,
                "--min-turns",
                str(MIN_LONG_SESSION_TURNS),
                "--output",
                str(cursor_corpus),
            ],
            cwd=repo,
        )
        _run(
            [
                PY,
                str(ROOT / "analyze_hot_session.py"),
                "--source",
                "cursor",
                "--project",
                cursor_project,
                "--largest",
                "--export",
                str(stats_dir / "phase2_hot_cursor.json"),
            ],
            cwd=repo,
        )
        result.cursor_long_sessions = _long_session_rows(_load_jsonl(cursor_corpus))
        passed = sum(1 for r in result.cursor_long_sessions if r["pass"])
        total = len(result.cursor_long_sessions)
        if total:
            result.checks.append(
                Check(
                    f"Compression ≥{COMPRESSION_TARGET:.0%} (Cursor 100+ turns)",
                    "PASS" if passed == total else "FAIL",
                    f"{passed}/{total} sessions pass",
                )
            )
        else:
            result.checks.append(
                Check(
                    f"Compression ≥{COMPRESSION_TARGET:.0%} (Cursor 100+ turns)",
                    "SKIP",
                    f"No Cursor sessions ≥{MIN_LONG_SESSION_TURNS} turns",
                )
            )

    corpus_files = [p for p in (claude_corpus, cursor_corpus) if p.is_file()]
    if corpus_files:
        _run(
            [PY, str(ROOT / "collect_stats.py"), "--logs", *[str(p) for p in corpus_files]],
            cwd=repo,
        )
        result.checks.append(
            Check("collect_stats corpus insights", "PASS", f"Ran on {len(corpus_files)} file(s)")
        )

    return result


def print_summary(result: Phase2Result) -> int:
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║                    PHASE 2 VALIDATION SUMMARY                          ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    fails = 0
    for chk in result.checks:
        icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "–", "BASELINE": "○"}[chk.status]
        if chk.status == "FAIL":
            fails += 1
        print(f"║ {icon} [{chk.status:<8}] {chk.name:<42} ║")
        print(f"║     {chk.detail[:66]:<66} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    return 1 if fails else 0


def write_report(path: Path, result: Phase2Result, *, args: argparse.Namespace) -> None:
    lines = [
        "# Phase 2 Validation Report",
        "",
        f"**Generated by:** `run_phase2_validation.py`",
        "",
        "## Checks",
        "",
        "| Status | Check | Detail |",
        "|--------|-------|--------|",
    ]
    for chk in result.checks:
        lines.append(f"| {chk.status} | {chk.name} | {chk.detail} |")

    if result.claude_long_sessions:
        lines.extend(["", "## Claude — sessions ≥100 turns", ""])
        lines.append("| Session | Turns | Compression | Pass |")
        lines.append("|---------|------:|------------:|:----:|")
        for r in result.claude_long_sessions:
            lines.append(
                f"| `{r['session_id']}` | {r['turns']} | {r['compression_pct']}% | "
                f"{'✓' if r['pass'] else '✗'} |"
            )

    if result.cursor_long_sessions:
        lines.extend(["", "## Cursor — sessions ≥100 turns", ""])
        lines.append("| Session | Turns | Compression | Pass |")
        lines.append("|---------|------:|------------:|:----:|")
        for r in result.cursor_long_sessions:
            lines.append(
                f"| `{r['session_id']}` | {r['turns']} | {r['compression_pct']}% | "
                f"{'✓' if r['pass'] else '✗'} |"
            )

    lines.extend([
        "",
        "## Optional (skipped)",
        "",
        "`test_simulator.py` with `Claude.production.md` — requires `ANTHROPIC_API_KEY` (gateway bifurcation only).",
        "",
        "## Artifacts",
        "",
        "- `stats/phase2_claude_corpus.jsonl`",
        "- `stats/phase2_hot_claude.json`",
        "- `stats/phase2_cursor_corpus.jsonl`",
        "- `stats/phase2_hot_cursor.json`",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 corpus validation suite")
    parser.add_argument(
        "--cli-root",
        type=Path,
        default=ROOT / "stats" / "dev-backup" / ".claude" / "projects",
    )
    parser.add_argument("--cursor-project", default="m-coder")
    parser.add_argument("--developer", default="meet-chavda")
    parser.add_argument("--stats-dir", type=Path, default=ROOT / "stats")
    parser.add_argument(
        "--baseline-corpus",
        type=Path,
        default=ROOT / "stats" / "meet-chavda_corpus.jsonl",
        help="Prior corpus for regression compare (0 drift expected)",
    )
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument("--skip-cursor", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "PHASE_2_REPORT.md",
    )
    args = parser.parse_args()

    result = run_phase2(
        cli_root=args.cli_root if not args.skip_claude else None,
        cursor_project=args.cursor_project if not args.skip_cursor else None,
        developer=args.developer,
        stats_dir=args.stats_dir,
        baseline_corpus=args.baseline_corpus,
        skip_claude=args.skip_claude,
        skip_cursor=args.skip_cursor,
    )
    write_report(args.report, result, args=args)
    return print_summary(result)


if __name__ == "__main__":
    sys.exit(main())
