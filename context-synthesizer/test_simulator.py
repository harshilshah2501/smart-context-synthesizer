#!/usr/bin/env python3
"""
JetBrains IDE client simulator for the context-synthesizer proxy gateway.

Fires 12 multi-turn chat requests to http://127.0.0.1:8080/v1/messages,
mimicking how JetBrains AI Assistant sends cumulative conversation threads.
Aggregates Anthropic usage fields and prints a cumulative benchmark report.

Usage:
    # Terminal 1 — start the proxy
    .venv/bin/python context-synthesizer/proxy_tool.py

    # Terminal 2 — run the simulator
    .venv/bin/python context-synthesizer/test_simulator.py

    # Optional flags
    .venv/bin/python context-synthesizer/test_simulator.py --base-url http://127.0.0.1:8080 --turns 12
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from models import DEFAULT_CHAT_MODEL

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL = DEFAULT_CHAT_MODEL

# Pricing per 1M tokens (matches proxy_tool.run_bifurcated_telemetry)
PRICE_UNCACHED_INPUT = 3.00
PRICE_CACHE_READ = 0.30
PRICE_CACHE_WRITE = 3.75
PRICE_OUTPUT = 15.00
PRICE_BASELINE_INPUT = 3.00


@dataclass
class TurnMetrics:
    turn: int
    label: str
    latency_s: float
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None

    @property
    def total_input_tokens(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    def baseline_cost(self) -> float:
        return (
            (self.total_input_tokens * PRICE_BASELINE_INPUT) + (self.output_tokens * PRICE_OUTPUT)
        ) / 1_000_000

    def realized_cost(self) -> float:
        return (
            (self.input_tokens * PRICE_UNCACHED_INPUT)
            + (self.cache_read_tokens * PRICE_CACHE_READ)
            + (self.cache_write_tokens * PRICE_CACHE_WRITE)
            + (self.output_tokens * PRICE_OUTPUT)
        ) / 1_000_000

    def dollars_saved(self) -> float:
        return self.baseline_cost() - self.realized_cost()

    def cache_efficiency_pct(self) -> float:
        total = self.total_input_tokens
        if total == 0:
            return 0.0
        return (self.cache_read_tokens / total) * 100.0


@dataclass
class BenchmarkReport:
    turns: list[TurnMetrics] = field(default_factory=list)

    def add(self, metrics: TurnMetrics) -> None:
        self.turns.append(metrics)

    def totals(self) -> TurnMetrics:
        agg = TurnMetrics(turn=0, label="CUMULATIVE", latency_s=sum(t.latency_s for t in self.turns))
        for t in self.turns:
            if t.error:
                continue
            agg.input_tokens += t.input_tokens
            agg.cache_read_tokens += t.cache_read_tokens
            agg.cache_write_tokens += t.cache_write_tokens
            agg.output_tokens += t.output_tokens
        return agg


def _generate_massive_code_block() -> str:
    """Synthetic multi-hundred-line source file to stress compaction logic."""
    header = textwrap.dedent(
        """
        Please review this entire module for performance bottlenecks and suggest refactors.
        The file is part of our JetBrains plugin's indexing pipeline.

        ```java
        package com.jetbrains.context.index;

        import java.util.*;
        import java.util.concurrent.*;
        import java.util.stream.*;

        /**
         * Simulated large codebase artifact — forces a bulky user turn through the proxy.
         */
        public class ContextIndexPipeline {
        """
    ).strip()

    lines = []
    for i in range(1, 201):
        lines.append(
            f"    private final Map<String, List<SymbolRef>> shard_{i} = new ConcurrentHashMap<>();"
        )
        if i % 10 == 0:
            lines.append(
                f"    public void reconcileShard_{i}() {{ shard_{i}.values().forEach(List::clear); }}"
            )

    footer = textwrap.dedent(
        """
            public void compact() {
                // Trigger background dreaming / ledger compaction on the proxy side.
                shard_1.keySet().forEach(k -> shard_50.merge(k, shard_100.getOrDefault(k, List.of()), (a, b) -> a));
            }
        }
        ```
        """
    ).strip()

    return f"{header}\n" + "\n".join(lines) + "\n" + footer


def build_jetbrains_prompts() -> list[tuple[str, str]]:
    """12 distinct prompts mimicking a JetBrains agent coding session."""
    massive = _generate_massive_code_block()
    return [
        ("bootstrap", "Initialize project context. What files should we index first in this repo?"),
        ("architecture", "Summarize the high-level architecture of a proxy that pins Claude.md at index 0."),
        ("cache-design", "Explain ephemeral cache_control boundaries for static vs synthesized history blocks."),
        ("jetbrains-format", "How does JetBrains AI Assistant typically structure multi-turn message payloads?"),
        ("index-layout", "Why must dynamic variables stay out of cached prefix blocks to avoid cache busting?"),
        ("telemetry", "What are input_tokens vs cache_read_input_tokens vs cache_creation_input_tokens?"),
        ("latency", "Suggest ways to keep proxy latency low while preserving cache hit rates."),
        ("streaming", "Should the proxy use streaming responses for IDE integrations? Pros and cons."),
        ("error-handling", "How should the gateway handle malformed message content from the IDE?"),
        ("threshold", "We're approaching the turn threshold — what should the history ledger compaction do?"),
        ("massive-code-review", massive),
        (
            "wrap-up",
            "Give a concise recap of cache savings achieved in this session and next optimization steps.",
        ),
    ]


def extract_usage(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
        "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }


def send_turn(
    client: httpx.Client,
    *,
    base_url: str,
    model: str,
    session_id: str,
    conversation: list[dict[str, Any]],
    turn_index: int,
    label: str,
    user_content: str,
) -> tuple[TurnMetrics, str | None]:
    """Send one JetBrains-style request; returns metrics and assistant text."""
    conversation.append({"role": "user", "content": user_content})

    body = {
        "model": model,
        "max_tokens": 1024,
        "messages": conversation,
    }

    start = time.perf_counter()
    try:
        response = client.post(
            f"{base_url.rstrip('/')}/v1/messages",
            json=body,
            headers={"X-Session-Id": session_id},
            timeout=180.0,
        )
        latency = time.perf_counter() - start

        if response.status_code != 200:
            return (
                TurnMetrics(turn=turn_index, label=label, latency_s=latency, error=response.text[:500]),
                None,
            )

        payload = response.json()
        usage = extract_usage(payload)

        assistant_text = ""
        for block in payload.get("content") or []:
            if block.get("type") == "text":
                assistant_text += block.get("text") or ""

        if assistant_text:
            conversation.append({"role": "assistant", "content": assistant_text})

        return (
            TurnMetrics(
                turn=turn_index,
                label=label,
                latency_s=latency,
                input_tokens=usage["input_tokens"],
                cache_read_tokens=usage["cache_read_input_tokens"],
                cache_write_tokens=usage["cache_creation_input_tokens"],
                output_tokens=usage["output_tokens"],
            ),
            assistant_text,
        )
    except httpx.HTTPError as exc:
        latency = time.perf_counter() - start
        return (
            TurnMetrics(turn=turn_index, label=label, latency_s=latency, error=str(exc)),
            None,
        )


def _bar(ratio: float, width: int = 40) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_turn_table(report: BenchmarkReport) -> None:
    print("\n┌──────┬──────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┐")
    print("│ Turn │ Label                │ Latency  │ Uncached │ Cache Rd │ Cache Wr │ Output   │")
    print("├──────┼──────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┤")
    for t in report.turns:
        if t.error:
            print(f"│ {t.turn:4d} │ {t.label[:20]:<20} │ {t.latency_s:7.2f}s │  ERROR   │          │          │          │")
            continue
        print(
            f"│ {t.turn:4d} │ {t.label[:20]:<20} │ {t.latency_s:7.2f}s │ "
            f"{t.input_tokens:8,} │ {t.cache_read_tokens:8,} │ {t.cache_write_tokens:8,} │ {t.output_tokens:8,} │"
        )
    print("└──────┴──────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┘")


def print_summary_report(report: BenchmarkReport) -> None:
    totals = report.totals()
    baseline = totals.baseline_cost()
    realized = totals.realized_cost()
    saved = totals.dollars_saved()
    savings_pct = (saved / baseline * 100.0) if baseline > 0 else 0.0
    cache_eff = totals.cache_efficiency_pct()

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║           CUMULATIVE CONTEXT ECONOMY BENCHMARK (12 TURNS)            ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Total Latency:              {sum(t.latency_s for t in report.turns):8.2f} seconds{' ' * 22}║")
    print(f"║ Uncached Input Tokens:      {totals.input_tokens:12,}{' ' * 24}║")
    print(f"║ Cache Read Tokens (90% off):{totals.cache_read_tokens:12,}{' ' * 24}║")
    print(f"║ Cache Write Tokens:         {totals.cache_write_tokens:12,}{' ' * 24}║")
    print(f"║ Output Tokens:              {totals.output_tokens:12,}{' ' * 24}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Baseline Total Cost (@$3/M): ${baseline:10.4f}{' ' * 28}║")
    print(f"║ Realized Cost (w/ caching):  ${realized:10.4f}{' ' * 28}║")
    print(f"║ Total Dollars Saved:         ${saved:10.4f}{' ' * 28}║")
    print(f"║ Savings Rate:                {savings_pct:9.1f}%{' ' * 30}║")
    print(f"║ Cache Efficiency Rate:       {cache_eff:9.1f}%  (cache reads / total input){' ' * 6}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ Cost composition (realized vs baseline input spend)                  ║")
    print(f"║   Baseline input: {_bar(1.0)} 100%{' ' * 28}║")
    print(f"║   Realized input: {_bar(realized / baseline if baseline else 0)} {realized/baseline*100 if baseline else 0:5.1f}%{' ' * 23}║")
    print(f"║   Cache hit share: {_bar(cache_eff / 100)} {cache_eff:5.1f}%{' ' * 23}║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    errors = [t for t in report.turns if t.error]
    if errors:
        print(f"\n⚠ {len(errors)} turn(s) failed:")
        for t in errors:
            print(f"  Turn {t.turn} ({t.label}): {t.error}")


def probe_proxy(client: httpx.Client, base_url: str) -> bool:
    try:
        response = client.get(f"{base_url.rstrip('/')}/docs", timeout=5.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def run_simulation(*, base_url: str, model: str, num_turns: int, session_id: str) -> int:
    prompts = build_jetbrains_prompts()[:num_turns]
    if len(prompts) < num_turns:
        print(f"Warning: only {len(prompts)} built-in prompts; running {len(prompts)} turns.")
        num_turns = len(prompts)

    report = BenchmarkReport()
    conversation: list[dict[str, Any]] = []

    print(f"JetBrains Client Simulator → {base_url}/v1/messages")
    print(f"Model: {model} | Turns: {num_turns} | Session: {session_id}")
    print("-" * 72)

    with httpx.Client() as client:
        if not probe_proxy(client, base_url):
            print(
                f"ERROR: Proxy not reachable at {base_url}.\n"
                "Start it first:\n"
                "  .venv/bin/python context-synthesizer/proxy_tool.py",
                file=sys.stderr,
            )
            return 1

        for idx, (label, user_content) in enumerate(prompts, start=1):
            print(f"[{idx:02d}/{num_turns}] {label} ... ", end="", flush=True)
            metrics, assistant_preview = send_turn(
                client,
                base_url=base_url,
                model=model,
                session_id=session_id,
                conversation=conversation,
                turn_index=idx,
                label=label,
                user_content=user_content,
            )
            report.add(metrics)

            if metrics.error:
                print(f"FAILED ({metrics.error[:80]})")
            else:
                preview = (assistant_preview or "").replace("\n", " ")[:60]
                print(f"OK ({metrics.latency_s:.2f}s, cache_read={metrics.cache_read_tokens:,}) — {preview}")

            # Brief pause so terminal telemetry from proxy is readable
            time.sleep(0.3)

    print_turn_table(report)
    print_summary_report(report)
    return 0 if not any(t.error for t in report.turns) else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate JetBrains IDE traffic against the proxy gateway.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Proxy base URL (default: %(default)s)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model id sent in request body")
    parser.add_argument("--turns", type=int, default=12, help="Number of conversation turns (max 12)")
    parser.add_argument(
        "--session-id",
        default="simulator-benchmark",
        help="X-Session-Id header value (default: simulator-benchmark)",
    )
    args = parser.parse_args()

    sys.exit(
        run_simulation(
            base_url=args.base_url,
            model=args.model,
            num_turns=args.turns,
            session_id=args.session_id,
        )
    )


if __name__ == "__main__":
    main()
