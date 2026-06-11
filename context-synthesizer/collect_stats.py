#!/usr/bin/env python3
"""
Aggregate bifurcated telemetry JSONL into a team report.

Aggregates JSONL from Modes A / C / D (and optional gateway logs), then prints
per-developer cost bifurcation and corpus compression insights.

Usage:
    .venv/bin/python context-synthesizer/collect_stats.py
    .venv/bin/python context-synthesizer/collect_stats.py --logs context-synthesizer/stats/
    .venv/bin/python context-synthesizer/collect_stats.py --export team_report.csv
    .venv/bin/python context-synthesizer/collect_stats.py --source proxy
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from telemetry import CostSnapshot, UsageSnapshot, compute_costs, MIN_CACHE_TOKENS

DEFAULT_STATS_DIR = Path(__file__).resolve().parent / "stats"


@dataclass
class AggregatedStats:
    requests: int = 0
    usage: UsageSnapshot = field(default_factory=UsageSnapshot)
    latency_total_s: float = 0.0
    compactions: int = 0

    def add(self, record: dict) -> None:
        self.requests += 1
        u = record.get("usage") or {}
        self.usage.input_tokens += int(u.get("input_tokens") or 0)
        self.usage.cache_read_input_tokens += int(u.get("cache_read_input_tokens") or 0)
        self.usage.cache_creation_input_tokens += int(u.get("cache_creation_input_tokens") or 0)
        self.usage.output_tokens += int(u.get("output_tokens") or 0)
        if record.get("latency_s"):
            self.latency_total_s += float(record["latency_s"])
        if record.get("compaction_triggered"):
            self.compactions += 1


def load_jsonl_files(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        if path.is_dir():
            files = sorted(path.glob("**/*.jsonl"))
        else:
            files = [path]
        for f in files:
            if not f.is_file():
                continue
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"WARN: skip {f}: {exc}", file=sys.stderr)
    return records


def _bar(ratio: float, width: int = 30) -> str:
    ratio = max(0.0, min(1.0, ratio))
    return "█" * int(ratio * width) + "░" * (width - int(ratio * width))


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pctile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(len(ordered) * p))
    return ordered[idx]


CORPUS_SOURCES = frozenset({"claude_corpus", "cursor_import"})


def print_corpus_insights(records: list[dict]) -> None:
    """Compression and session-shape metrics from Mode D/C exports."""
    corpus = [r for r in records if r.get("source") in CORPUS_SOURCES]
    if not corpus:
        return

    ratios: list[float] = []
    long_session_ratios: list[float] = []
    for rec in corpus:
        extra = rec.get("extra") or {}
        ratio = extra.get("compression_ratio_est")
        if ratio is None:
            continue
        ratios.append(float(ratio))
        turns = int(rec.get("turn_number") or 0)
        if turns >= 100:
            long_session_ratios.append(float(ratio))

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║           CORPUS INSIGHTS (Mode D / C exports)                         ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Sessions:              {len(corpus):>8,}{' ' * 39}║")
    if ratios:
        print(f"║ Avg compression est:   {_avg(ratios) * 100:>7.1f}%{' ' * 39}║")
        print(f"║ p90 compression est:   {_pctile(ratios, 0.9) * 100:>7.1f}%{' ' * 39}║")
    if long_session_ratios:
        print(f"║ 100+ turn sessions:    {len(long_session_ratios):>8,}{' ' * 39}║")
        print(f"║ 100+ turn avg save:    {_avg(long_session_ratios) * 100:>7.1f}%{' ' * 39}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ Deep-dive one session: analyze_hot_session.py --source claude|cursor ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")


def print_synthesizer_insights(records: list[dict]) -> None:
    """Actionable metrics for tuning compaction thresholds, ledger size, and cache layers."""
    proxy = [r for r in records if r.get("source") == "proxy"]
    compactions = [r for r in records if r.get("source") == "compaction"]
    if not proxy:
        print("\n(No proxy events in logs — synthesizer tuning insights need gateway telemetry.")
        print("For corpus-based tuning, use analyze_hot_session.py on Mode D/C exports.")
        return

    uncached_pcts: list[float] = []
    cache_read_pcts: list[float] = []
    bloat_ratios: list[float] = []
    l3_l4_est: list[int] = []
    l3_l4_actual: list[int] = []
    ledger_chars: list[int] = []
    l1_eligible = 0
    savings_pcts: list[float] = []

    turn_buckets: dict[str, list[float]] = {"1-3": [], "4-10": [], "11+": []}

    for rec in proxy:
        syn = rec.get("synthesis") or {}
        ctx = rec.get("context") or {}
        cost = rec.get("cost") or {}
        turn = int(rec.get("turn_number") or ctx.get("turn_number") or 0)

        uncached_pcts.append(float(syn.get("uncached_tail_pct") or 0))
        cache_read_pcts.append(float(syn.get("cache_read_pct") or 0))
        bloat_ratios.append(float(syn.get("client_bloat_ratio") or 0))
        l3_l4_est.append(int(syn.get("est_l3_l4_tokens") or 0))
        l3_l4_actual.append(int(syn.get("uncached_tail_tokens") or 0))
        ledger_chars.append(int(ctx.get("ledger_chars") or 0))
        savings_pcts.append(float(cost.get("savings_pct") or 0))
        if ctx.get("l1_cache_eligible_est"):
            l1_eligible += 1

        bucket = "1-3" if turn <= 3 else ("4-10" if turn <= 10 else "11+")
        turn_buckets[bucket].append(float(syn.get("uncached_tail_pct") or 0))

    compaction_cost = sum((r.get("cost") or {}).get("actual_usd", 0) for r in compactions)
    ledger_shrink: list[int] = [
        int((r.get("extra") or {}).get("ledger_delta_chars") or 0) for r in compactions
    ]

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║           SYNTHESIZER TUNING INSIGHTS (gateway proxy events)         ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Proxy requests:        {len(proxy):>8,}{' ' * 39}║")
    print(f"║ Compaction runs:       {len(compactions):>8,}  (${compaction_cost:.4f} Haiku cost){' ' * 15}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ CACHE & TAIL (lower uncached tail → better synthesizer)              ║")
    print(f"║ Avg uncached tail:     {_avg(uncached_pcts):>7.1f}%   p90: {_pctile(uncached_pcts, 0.9):>6.1f}%{' ' * 22}║")
    print(f"║ Avg cache read share:  {_avg(cache_read_pcts):>7.1f}%{' ' * 39}║")
    print(f"║ Avg savings / request: {_avg(savings_pcts):>7.1f}%{' ' * 39}║")
    print(f"║ L1 cache-eligible est:{l1_eligible / len(proxy) * 100:>7.1f}% of requests{' ' * 28}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ CONTEXT SHAPE (chars → tune MAX_TURNS_THRESHOLD & ledger cap)        ║")
    print(f"║ Avg ledger size:       {_avg(ledger_chars):>8,.0f} chars{' ' * 31}║")
    print(f"║ Avg client bloat:      {_avg(bloat_ratios):>7.1f}x IDE msgs vs proxy payload{' ' * 18}║")
    print(f"║ Est L3+L4 tokens:      {_avg(l3_l4_est):>8,.0f}   actual uncached: {_avg(l3_l4_actual):>8,.0f}{' ' * 7}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ UNCACHED TAIL BY TURN BUCKET (compaction window)                     ║")
    for label, vals in turn_buckets.items():
        if vals:
            print(f"║   Turn {label:<5}  avg tail { _avg(vals):>6.1f}%  (n={len(vals):>4}){' ' * 24}║")
    if compactions:
        print("╠══════════════════════════════════════════════════════════════════════╣")
        print("║ COMPACTION EFFECTIVENESS                                             ║")
        print(f"║ Avg ledger delta:      {_avg([float(x) for x in ledger_shrink]):>+8,.0f} chars/run{' ' * 28}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ RECOMMENDATIONS                                                      ║")
    recs = _synthesizer_recommendations(
        proxy_count=len(proxy),
        l1_eligible_pct=l1_eligible / len(proxy) * 100,
        avg_uncached_tail=_avg(uncached_pcts),
        avg_cache_read=_avg(cache_read_pcts),
        avg_bloat=_avg(bloat_ratios),
        avg_ledger=_avg(ledger_chars),
        compaction_count=len(compactions),
    )
    for rec in recs:
        line = rec[:68]
        print(f"║ • {line:<68} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")


def _synthesizer_recommendations(
    *,
    proxy_count: int,
    l1_eligible_pct: float,
    avg_uncached_tail: float,
    avg_cache_read: float,
    avg_bloat: float,
    avg_ledger: float,
    compaction_count: int,
) -> list[str]:
    recs: list[str] = []
    if l1_eligible_pct < 50:
        recs.append(
            f"Expand Claude.md to ≥{MIN_CACHE_TOKENS} tokens — only {l1_eligible_pct:.0f}% "
            "of requests hit L1 cache threshold"
        )
    if avg_cache_read < 40:
        recs.append("Low cache read share — warm sessions or enlarge cached L1/L2 prefix")
    if avg_uncached_tail > 35:
        recs.append("High uncached tail — lower MAX_TURNS_THRESHOLD or tighten compaction prompt")
    if avg_ledger > 12_000:
        recs.append("Ledger growing large — cap compaction output or trigger earlier")
    if avg_bloat > 5:
        recs.append(f"IDE sends {avg_bloat:.0f}x more messages than proxy — synthesizer is high value")
    if proxy_count >= 20 and compaction_count == 0:
        recs.append("No compactions yet — sessions may be short; collect longer sessions")
    if not recs:
        recs.append("Metrics look healthy — keep collecting for per-project breakdowns")
    return recs[:5]


def print_report(
    records: list[dict],
    *,
    group_by: str,
    source_filter: str | None,
) -> None:
    if source_filter:
        records = [r for r in records if r.get("source") == source_filter]

    if not records:
        print("No telemetry records found.")
        return

    buckets: dict[str, AggregatedStats] = defaultdict(AggregatedStats)
    team = AggregatedStats()

    for rec in records:
        key = rec.get(group_by) or "unknown"
        buckets[key].add(rec)
        team.add(rec)

    team_cost = compute_costs(team.usage)

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║              TEAM BIFURCATED TOKEN ECONOMY REPORT                    ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Total requests:     {team.requests:>10,}{' ' * 38}║")
    print(f"║ Uncached input:     {team.usage.input_tokens:>10,}{' ' * 38}║")
    print(f"║ Cache read (90%):   {team.usage.cache_read_input_tokens:>10,}{' ' * 38}║")
    print(f"║ Cache write:        {team.usage.cache_creation_input_tokens:>10,}{' ' * 38}║")
    print(f"║ Output:             {team.usage.output_tokens:>10,}{' ' * 38}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Baseline cost:      ${team_cost.baseline_usd:>10.4f}{' ' * 35}║")
    print(f"║ Actual cost:        ${team_cost.actual_usd:>10.4f}{' ' * 35}║")
    print(f"║ Total saved:        ${team_cost.saved_usd:>10.4f}  ({team_cost.savings_pct:.1f}%){' ' * 24}║")
    print(f"║ Cache efficiency:   {team_cost.cache_efficiency_pct:>9.1f}%{' ' * 38}║")
    if team.requests:
        print(f"║ Avg latency:        {team.latency_total_s / team.requests:>9.2f}s{' ' * 38}║")
    print(f"║ Compactions logged:  {team.compactions:>10,}{' ' * 38}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ By {group_by:<62} ║")
    print("╠══════════════════╦═════════╦═══════════╦═══════════╦═══════════╦══════════╣")
    print("║ Group            ║ Reqs    ║ Cache Rd  ║ Uncached  ║ Saved %   ║ Actual $ ║")
    print("╠══════════════════╬═════════╬═══════════╬═══════════╬═══════════╬══════════╣")

    for key in sorted(buckets.keys()):
        agg = buckets[key]
        cost = compute_costs(agg.usage)
        label = str(key)[:16]
        print(
            f"║ {label:<16} ║ {agg.requests:7,} ║ {agg.usage.cache_read_input_tokens:9,} ║ "
            f"{agg.usage.input_tokens:9,} ║ {cost.savings_pct:8.1f}% ║ ${cost.actual_usd:7.4f} ║"
        )

    print("╚══════════════════╩═════════╩═══════════╩═══════════╩═══════════╩══════════╝")

    print("\nCost composition:")
    print(f"  Baseline: {_bar(1.0)} 100%")
    if team_cost.baseline_usd > 0:
        print(f"  Actual:   {_bar(team_cost.actual_usd / team_cost.baseline_usd)} "
              f"{team_cost.actual_usd / team_cost.baseline_usd * 100:.1f}%")
        print(f"  Cache hit share: {_bar(team_cost.cache_efficiency_pct / 100)} "
              f"{team_cost.cache_efficiency_pct:.1f}% of input tokens")

    sources = defaultdict(int)
    for r in records:
        sources[r.get("source", "unknown")] += 1
    print(f"\nSources: {dict(sources)}")


def export_csv(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "ts", "source", "developer_id", "session_id", "model", "latency_s",
        "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
        "output_tokens", "actual_usd", "baseline_usd", "saved_usd", "savings_pct",
        "cache_efficiency_pct", "compaction_triggered", "client", "project_path",
        "turn_number", "lifetime_turn", "layer3_messages", "client_message_count",
        "ignored_messages", "est_layer1_tokens", "est_ledger_tokens", "est_layer3_tokens",
        "est_prompt_tokens", "uncached_tail_pct", "cache_read_pct", "client_bloat_ratio",
        "turns_compacted", "ledger_chars_before", "ledger_chars_after",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for rec in records:
            u = rec.get("usage") or {}
            c = rec.get("cost") or {}
            ctx = rec.get("context") or {}
            syn = rec.get("synthesis") or {}
            extra = rec.get("extra") or {}
            writer.writerow({
                "ts": rec.get("ts"),
                "source": rec.get("source"),
                "developer_id": rec.get("developer_id"),
                "session_id": rec.get("session_id"),
                "model": rec.get("model"),
                "latency_s": rec.get("latency_s"),
                "input_tokens": u.get("input_tokens"),
                "cache_read_input_tokens": u.get("cache_read_input_tokens"),
                "cache_creation_input_tokens": u.get("cache_creation_input_tokens"),
                "output_tokens": u.get("output_tokens"),
                "actual_usd": c.get("actual_usd"),
                "baseline_usd": c.get("baseline_usd"),
                "saved_usd": c.get("saved_usd"),
                "savings_pct": c.get("savings_pct"),
                "cache_efficiency_pct": c.get("cache_efficiency_pct"),
                "compaction_triggered": rec.get("compaction_triggered"),
                "client": rec.get("client"),
                "project_path": rec.get("project_path"),
                "turn_number": rec.get("turn_number") or ctx.get("turn_number"),
                "lifetime_turn": ctx.get("lifetime_turn"),
                "layer3_messages": rec.get("layer3_messages") or ctx.get("layer3_messages"),
                "client_message_count": ctx.get("client_message_count"),
                "ignored_messages": ctx.get("ignored_messages"),
                "est_layer1_tokens": ctx.get("est_layer1_tokens"),
                "est_ledger_tokens": ctx.get("est_ledger_tokens"),
                "est_layer3_tokens": ctx.get("est_layer3_tokens"),
                "est_prompt_tokens": ctx.get("est_prompt_tokens"),
                "uncached_tail_pct": syn.get("uncached_tail_pct"),
                "cache_read_pct": syn.get("cache_read_pct"),
                "client_bloat_ratio": syn.get("client_bloat_ratio"),
                "turns_compacted": extra.get("turns_compacted"),
                "ledger_chars_before": extra.get("ledger_chars_before"),
                "ledger_chars_after": extra.get("ledger_chars_after"),
            })
    print(f"Exported {len(records)} rows → {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate team telemetry JSONL into bifurcation report.")
    parser.add_argument(
        "--logs",
        nargs="+",
        type=Path,
        default=[DEFAULT_STATS_DIR],
        help="JSONL files or directories (default: context-synthesizer/stats/)",
    )
    parser.add_argument(
        "--group-by",
        choices=["developer_id", "session_id", "model", "source", "client"],
        default="developer_id",
    )
    parser.add_argument(
        "--source",
        choices=["cli_import", "claude_corpus", "cursor_import", "proxy", "compaction"],
        help="Filter by JSONL source tag",
    )
    parser.add_argument("--export", type=Path, help="Export flattened CSV for spreadsheets")
    parser.add_argument(
        "--no-insights",
        action="store_true",
        help="Skip synthesizer tuning insights section",
    )
    args = parser.parse_args()

    records = load_jsonl_files(args.logs)
    print_report(records, group_by=args.group_by, source_filter=args.source)
    if not args.no_insights:
        print_corpus_insights(records)
        print_synthesizer_insights(records)
    if args.export:
        filtered = records if not args.source else [r for r in records if r.get("source") == args.source]
        export_csv(filtered, args.export)
    return 0


if __name__ == "__main__":
    sys.exit(main())
