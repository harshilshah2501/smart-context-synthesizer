#!/usr/bin/env python3
"""Capture an illustrative dashboard PNG for README / docs.

Writes *synthetic* 12-turn telemetry so the layout is reproducible without an
API key. Dollar and percent figures are not a measured Claude Code session —
do not quote them as product benchmarks. For real numbers, run
``python test_simulator.py`` against a live proxy.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "stats"
SAMPLE_LOG = STATS / "sample-telemetry.jsonl"
DEFAULT_OUT = ROOT.parent / "docs" / "assets" / "dashboard-snapshot.png"


def _ts(offset_min: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=30 - offset_min)).isoformat()


def build_sample_events() -> list[dict]:
    """12-turn session with compaction at turn 10 — realistic dashboard shape."""
    session = "demo-session-12"
    dev = "harshil.shah"
    events: list[dict] = []

    l1_tokens = 1680
    ledger_tokens = 0
    naive = 2200

    for turn in range(1, 13):
        ledger_tokens = 420 if turn >= 10 else max(0, (turn - 1) * 35)
        l3_tokens = min(turn * 180, 1800)
        l4_tokens = 120 + turn * 8
        shaped = l1_tokens + ledger_tokens + l3_tokens + l4_tokens
        naive = naive + 1400 + turn * 120

        cache_read = 0 if turn <= 2 else int(l1_tokens + ledger_tokens + l3_tokens * 0.6)
        cache_write = int(l1_tokens + ledger_tokens) if turn in (3, 10) else 0
        uncached = max(180, l4_tokens + int(l3_tokens * 0.4))
        output = 280 + turn * 15

        total_in = cache_read + cache_write + uncached
        actual = (
            uncached * 3.0 + cache_read * 0.30 + cache_write * 3.75 + output * 15.0
        ) / 1_000_000
        baseline = (total_in * 3.0 + output * 15.0) / 1_000_000
        saved = max(0.0, baseline - actual)
        savings_pct = (saved / baseline * 100) if baseline else 0.0

        events.append(
            {
                "ts": _ts(turn),
                "source": "proxy",
                "developer_id": dev,
                "session_id": session,
                "model": "claude-sonnet-4-6",
                "latency_s": 1.2 + turn * 0.08,
                "turn_number": turn,
                "layer3_messages": min(turn, 10),
                "compaction_triggered": turn == 10,
                "client": "claude-code",
                "usage": {
                    "input_tokens": uncached,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_write,
                    "output_tokens": output,
                },
                "cost": {
                    "actual_usd": round(actual, 4),
                    "baseline_usd": round(baseline, 4),
                    "saved_usd": round(saved, 4),
                    "savings_pct": round(savings_pct, 1),
                    "cache_efficiency_pct": round(
                        cache_read / total_in * 100 if total_in else 0, 1
                    ),
                },
                "context": {
                    "layer1_chars": l1_tokens * 4,
                    "ledger_chars": ledger_tokens * 4,
                    "layer3_chars": l3_tokens * 4,
                    "prompt_chars": l4_tokens * 4,
                    "client_message_count": turn * 3,
                    "pinned_checkpoints": 1 if turn >= 8 else 0,
                    "checkpoint_chars": 120 if turn >= 8 else 0,
                    "turn_number": turn,
                    "est_layer1_tokens": l1_tokens,
                    "est_checkpoint_tokens": 30 if turn >= 8 else 0,
                    "est_ledger_tokens": ledger_tokens,
                    "est_layer3_tokens": l3_tokens,
                    "est_prompt_tokens": l4_tokens,
                    "est_payload_tokens": shaped,
                    "est_naive_tokens": naive,
                    "compression_vs_naive_pct": round(
                        max(0, (1 - shaped / naive) * 100), 1
                    ),
                    "l1_cache_eligible_est": True,
                    "optimized_message_count": 4,
                },
                "synthesis": {
                    "total_input_tokens": total_in,
                    "uncached_tail_tokens": uncached,
                    "uncached_tail_pct": round(uncached / total_in * 100, 1),
                    "cache_read_pct": round(cache_read / total_in * 100, 1),
                    "cache_write_pct": round(cache_write / total_in * 100, 1),
                    "client_bloat_ratio": round(turn * 0.9, 1),
                    "est_naive_tokens": naive,
                    "est_shaped_tokens": shaped,
                    "compression_vs_naive_pct": round(
                        max(0, (1 - shaped / naive) * 100), 1
                    ),
                },
            }
        )

    events.append(
        {
            "ts": _ts(10),
            "source": "compaction",
            "developer_id": dev,
            "session_id": session,
            "model": "claude-haiku-4-5-20251001",
            "latency_s": 2.4,
            "usage": {
                "input_tokens": 8200,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "output_tokens": 1100,
            },
            "cost": {"actual_usd": 0.0041, "baseline_usd": 0.0041, "saved_usd": 0.0, "savings_pct": 0.0, "cache_efficiency_pct": 0.0},
            "extra": {
                "turns_compacted": 8,
                "ledger_chars_before": 0,
                "ledger_chars_after": 1680,
                "ledger_delta_chars": 1680,
                "trigger_reason": "turn_threshold",
                "pins_active": 1,
            },
        }
    )
    return events


def write_sample_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events = build_sample_events()
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def capture_with_playwright(url: str, out: Path) -> None:
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1600})
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_selector("#compareHero .compare-card", timeout=15000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(out), full_page=True)
        browser.close()


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    port = int(os.environ.get("SNAPSHOT_PORT", "8765"))
    write_sample_log(SAMPLE_LOG)

    env = os.environ.copy()
    env["TELEMETRY_LOG_PATH"] = str(SAMPLE_LOG)
    env["PYTHONPATH"] = str(ROOT)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "proxy_tool:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/dashboard"
    try:
        import httpx

        for _ in range(40):
            try:
                r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.25)
        else:
            print("Proxy failed to start", file=sys.stderr)
            return 1

        capture_with_playwright(url, out)
        print(f"Wrote {out}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
