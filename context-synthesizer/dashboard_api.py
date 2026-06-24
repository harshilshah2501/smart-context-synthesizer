"""
Aggregate bifurcated telemetry for the live dashboard API.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from telemetry import MIN_CACHE_TOKENS, TELEMETRY_LOG_PATH, get_live_events


def _avg(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _pctile(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    ordered = sorted(vals)
    idx = min(len(ordered) - 1, int(p * len(ordered)))
    return ordered[idx]


def load_jsonl_events(
    path: Path | None = None,
    *,
    limit: int = 500,
    developer_id: str | None = None,
    session_id: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    log_path = path or TELEMETRY_LOG_PATH
    if not log_path.is_file():
        return []

    lines: list[str] = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                lines.append(line)
    if limit > 0:
        lines = lines[-limit:]

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if developer_id and rec.get("developer_id") != developer_id:
            continue
        if session_id and rec.get("session_id") != session_id:
            continue
        if source and rec.get("source") != source:
            continue
        events.append(rec)
    return events


def merge_events(
    *,
    file_limit: int = 500,
    live_since: int = 0,
    developer_id: str | None = None,
    session_id: str | None = None,
    source: str | None = None,
    log_path: Path | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Merge JSONL tail with in-memory live buffer (live wins on duplicate keys)."""
    file_events = load_jsonl_events(
        log_path,
        limit=file_limit,
        developer_id=developer_id,
        session_id=session_id,
        source=source,
    )
    live_slice, live_total = get_live_events(since_index=0)
    if developer_id:
        live_slice = [e for e in live_slice if e.get("developer_id") == developer_id]
    if session_id:
        live_slice = [e for e in live_slice if e.get("session_id") == session_id]
    if source:
        live_slice = [e for e in live_slice if e.get("source") == source]

    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    def _key(ev: dict[str, Any]) -> str:
        return "|".join(
            str(ev.get(k, ""))
            for k in ("ts", "source", "session_id", "turn_number", "model", "developer_id")
        )

    for ev in live_slice + file_events:
        key = _key(ev)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ev)

    merged.sort(key=lambda e: e.get("ts") or "")
    if file_limit > 0 and len(merged) > file_limit:
        merged = merged[-file_limit:]

    return merged, live_total


def list_filter_options(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    devs = sorted({str(e.get("developer_id") or "") for e in events if e.get("developer_id")})
    sessions = sorted({str(e.get("session_id") or "") for e in events if e.get("session_id")})
    return {"developers": devs, "sessions": sessions}


def aggregate_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    proxy = [e for e in events if e.get("source") == "proxy"]
    compactions = [e for e in events if e.get("source") == "compaction"]

    savings_pcts: list[float] = []
    cache_read_pcts: list[float] = []
    uncached_pcts: list[float] = []
    bloat_ratios: list[float] = []
    compression_pcts: list[float] = []
    actual_cost = 0.0
    baseline_cost = 0.0
    saved_cost = 0.0
    compaction_cost = 0.0

    for rec in proxy:
        cost = rec.get("cost") or {}
        syn = rec.get("synthesis") or {}
        actual_cost += float(cost.get("actual_usd") or 0)
        baseline_cost += float(cost.get("baseline_usd") or 0)
        saved_cost += float(cost.get("saved_usd") or 0)
        savings_pcts.append(float(cost.get("savings_pct") or 0))
        cache_read_pcts.append(float(syn.get("cache_read_pct") or 0))
        uncached_pcts.append(float(syn.get("uncached_tail_pct") or 0))
        bloat_ratios.append(float(syn.get("client_bloat_ratio") or 0))
        compression_pcts.append(float(syn.get("compression_vs_naive_pct") or 0))

    for rec in compactions:
        compaction_cost += float((rec.get("cost") or {}).get("actual_usd") or 0)

    l1_eligible = sum(
        1 for r in proxy if (r.get("context") or {}).get("l1_cache_eligible_est")
    )

    total_cache_read = 0
    total_cache_write = 0
    total_uncached = 0
    total_output = 0
    for rec in proxy:
        usage = rec.get("usage") or {}
        total_cache_read += int(usage.get("cache_read_input_tokens") or 0)
        total_cache_write += int(usage.get("cache_creation_input_tokens") or 0)
        total_uncached += int(usage.get("input_tokens") or 0)
        total_output += int(usage.get("output_tokens") or 0)

    # Payload size is per-turn (IDE history vs shaped) — use latest turn, not a sum.
    latest_naive_tokens = 0
    latest_shaped_tokens = 0
    latest_compression_pct = 0.0
    latest_turn_number = 0
    peak_naive_tokens = 0
    if proxy:
        last = proxy[-1]
        last_syn = last.get("synthesis") or {}
        last_ctx = last.get("context") or {}
        latest_naive_tokens = int(
            last_syn.get("est_naive_tokens") or last_ctx.get("est_naive_tokens") or 0
        )
        latest_shaped_tokens = int(
            last_syn.get("est_shaped_tokens") or last_ctx.get("est_payload_tokens") or 0
        )
        latest_compression_pct = float(
            last_syn.get("compression_vs_naive_pct") or last_ctx.get("compression_vs_naive_pct") or 0
        )
        latest_turn_number = int(
            last.get("turn_number") or last_ctx.get("turn_number") or 0
        )
        for rec in proxy:
            ctx = rec.get("context") or {}
            syn = rec.get("synthesis") or {}
            naive = int(syn.get("est_naive_tokens") or ctx.get("est_naive_tokens") or 0)
            peak_naive_tokens = max(peak_naive_tokens, naive)

    total_input_billed = total_cache_read + total_cache_write + total_uncached
    cost_savings_pct = (
        round((saved_cost / baseline_cost) * 100, 1) if baseline_cost > 0 else 0.0
    )

    # Active pins: take the value from the most recent proxy event
    active_pins = 0
    for rec in reversed(proxy):
        pins = (rec.get("context") or {}).get("pinned_checkpoints")
        if pins is not None:
            active_pins = int(pins)
            break

    return {
        "total_events": len(events),
        "proxy_requests": len(proxy),
        "compaction_runs": len(compactions),
        "compaction_cost_usd": round(compaction_cost, 4),
        "actual_cost_usd": round(actual_cost, 4),
        "baseline_cost_usd": round(baseline_cost, 4),
        "saved_cost_usd": round(saved_cost, 4),
        "avg_savings_pct": round(_avg(savings_pcts), 1),
        "avg_cache_read_pct": round(_avg(cache_read_pcts), 1),
        "avg_uncached_tail_pct": round(_avg(uncached_pcts), 1),
        "avg_bloat_ratio": round(_avg(bloat_ratios), 1),
        "avg_compression_vs_naive_pct": round(_avg(compression_pcts), 1),
        "p90_compression_vs_naive_pct": round(_pctile(compression_pcts, 0.9), 1),
        "l1_cache_eligible_pct": round(l1_eligible / len(proxy) * 100, 1) if proxy else 0.0,
        "active_pins": active_pins,
        "latest_naive_tokens": latest_naive_tokens,
        "latest_shaped_tokens": latest_shaped_tokens,
        "latest_compression_pct": round(latest_compression_pct, 1),
        "latest_turn_number": latest_turn_number,
        "peak_naive_tokens": peak_naive_tokens,
        "total_cache_read": total_cache_read,
        "total_cache_write": total_cache_write,
        "total_uncached": total_uncached,
        "total_output": total_output,
        "total_input_billed": total_input_billed,
        "cost_savings_pct": cost_savings_pct,
    }


def build_chart_series(events: list[dict[str, Any]], *, max_points: int = 60) -> dict[str, Any]:
    proxy = [e for e in events if e.get("source") == "proxy"]
    if max_points > 0 and len(proxy) > max_points:
        proxy = proxy[-max_points:]

    labels: list[str] = []
    cache_read: list[int] = []
    cache_write: list[int] = []
    uncached: list[int] = []
    output: list[int] = []
    l1: list[int] = []
    l2a: list[int] = []
    l2: list[int] = []
    l3: list[int] = []
    l4: list[int] = []
    naive: list[int] = []
    shaped: list[int] = []
    cum_actual: list[float] = []
    cum_baseline: list[float] = []
    compression_pct: list[float] = []
    uncached_pct: list[float] = []

    run_actual = 0.0
    run_baseline = 0.0

    for rec in proxy:
        turn = rec.get("turn_number") or rec.get("context", {}).get("turn_number") or "?"
        labels.append(f"T{turn}")
        usage = rec.get("usage") or {}
        cost = rec.get("cost") or {}
        ctx = rec.get("context") or {}
        syn = rec.get("synthesis") or {}

        cache_read.append(int(usage.get("cache_read_input_tokens") or 0))
        cache_write.append(int(usage.get("cache_creation_input_tokens") or 0))
        uncached.append(int(usage.get("input_tokens") or 0))
        output.append(int(usage.get("output_tokens") or 0))

        l1.append(int(ctx.get("est_layer1_tokens") or 0))
        l2a.append(int(ctx.get("est_checkpoint_tokens") or 0))
        l2.append(int(ctx.get("est_ledger_tokens") or 0))
        l3.append(int(ctx.get("est_layer3_tokens") or 0))
        l4.append(int(ctx.get("est_prompt_tokens") or 0))
        naive.append(int(syn.get("est_naive_tokens") or ctx.get("est_naive_tokens") or 0))
        shaped.append(int(syn.get("est_shaped_tokens") or ctx.get("est_payload_tokens") or 0))

        run_actual += float(cost.get("actual_usd") or 0)
        run_baseline += float(cost.get("baseline_usd") or 0)
        cum_actual.append(round(run_actual, 4))
        cum_baseline.append(round(run_baseline, 4))
        compression_pct.append(float(syn.get("compression_vs_naive_pct") or 0))
        uncached_pct.append(float(syn.get("uncached_tail_pct") or 0))

    return {
        "labels": labels,
        "billing": {
            "cache_read": cache_read,
            "cache_write": cache_write,
            "uncached": uncached,
            "output": output,
        },
        "layers": {"l1": l1, "l2a": l2a, "l2": l2, "l3": l3, "l4": l4},
        "shape_compare": {"naive": naive, "shaped": shaped},
        "cumulative_cost": {"actual": cum_actual, "baseline": cum_baseline},
        "trends": {"compression_pct": compression_pct, "uncached_tail_pct": uncached_pct},
    }


def compaction_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in events:
        if rec.get("source") != "compaction":
            continue
        extra = rec.get("extra") or {}
        rows.append(
            {
                "ts": rec.get("ts"),
                "session_id": rec.get("session_id"),
                "turns_compacted": extra.get("turns_compacted"),
                "ledger_before": extra.get("ledger_chars_before"),
                "ledger_after": extra.get("ledger_chars_after"),
                "ledger_delta": extra.get("ledger_delta_chars"),
                "trigger": extra.get("trigger_reason"),
                "pins_active": extra.get("pins_active", 0),
                "cost_usd": (rec.get("cost") or {}).get("actual_usd"),
            }
        )
    return rows[-30:]


def recommendations(summary: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    if summary["proxy_requests"] == 0:
        return ["No proxy events yet — use Claude Code with ANTHROPIC_BASE_URL pointing at this proxy."]

    if summary["l1_cache_eligible_pct"] < 50:
        recs.append(
            f"Expand Claude.md to ≥{MIN_CACHE_TOKENS} tokens — only "
            f"{summary['l1_cache_eligible_pct']:.0f}% of requests hit L1 cache threshold."
        )
    if summary["avg_cache_read_pct"] < 40:
        recs.append("Low cache read share — warm sessions or enlarge cached L1/L2 prefix.")
    if summary["avg_uncached_tail_pct"] > 35:
        recs.append("High uncached tail — lower MAX_TURNS_THRESHOLD or tighten compaction prompt.")
    if summary["avg_bloat_ratio"] > 5:
        recs.append(
            f"IDE sends {summary['avg_bloat_ratio']:.0f}× more messages than proxy — synthesizer is high value."
        )
    if summary["proxy_requests"] >= 10 and summary["compaction_runs"] == 0:
        recs.append("No compactions yet — session may be short; keep coding to trigger Dreaming.")
    if summary["avg_compression_vs_naive_pct"] > 50:
        recs.append(
            f"Live shaped payload is ~{summary['avg_compression_vs_naive_pct']:.0f}% smaller than full IDE history."
        )
    if summary.get("compaction_runs", 0) > 0 and summary.get("active_pins", 0) == 0:
        recs.append(
            "Compactions are running — use @synth-remember: in a message to pin "
            "critical facts (bug fixes, migrations) so they survive every compaction."
        )
    if not recs:
        recs.append("Metrics look healthy — keep collecting for per-project breakdowns.")
    return recs[:6]


def recent_table_rows(events: list[dict[str, Any]], *, limit: int = 40) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in reversed(events):
        if rec.get("source") != "proxy":
            continue
        usage = rec.get("usage") or {}
        cost = rec.get("cost") or {}
        ctx = rec.get("context") or {}
        syn = rec.get("synthesis") or {}
        rows.append(
            {
                "ts": rec.get("ts"),
                "turn": rec.get("turn_number"),
                "session_id": (rec.get("session_id") or "")[:12],
                "cache_read": usage.get("cache_read_input_tokens"),
                "cache_write": usage.get("cache_creation_input_tokens"),
                "uncached": usage.get("input_tokens"),
                "output": usage.get("output_tokens"),
                "l1": ctx.get("est_layer1_tokens"),
                "l2": ctx.get("est_ledger_tokens"),
                "l3": ctx.get("est_layer3_tokens"),
                "l4": ctx.get("est_prompt_tokens"),
                "naive_est": syn.get("est_naive_tokens") or ctx.get("est_naive_tokens"),
                "shaped_est": syn.get("est_shaped_tokens") or ctx.get("est_payload_tokens"),
                "compression_pct": syn.get("compression_vs_naive_pct"),
                "savings_pct": cost.get("savings_pct"),
                "saved_usd": cost.get("saved_usd"),
                "bloat": syn.get("client_bloat_ratio"),
                "compacted": rec.get("compaction_triggered"),
                "pins": (rec.get("context") or {}).get("pinned_checkpoints", 0),
                "latency_s": rec.get("latency_s"),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def dashboard_payload(
    *,
    limit: int = 500,
    developer_id: str | None = None,
    session_id: str | None = None,
    source: str | None = None,
    chart_points: int = 60,
    log_path: Path | None = None,
) -> dict[str, Any]:
    events, live_total = merge_events(
        file_limit=limit,
        developer_id=developer_id,
        session_id=session_id,
        source=source,
        log_path=log_path,
    )
    summary = aggregate_summary(events)
    return {
        "summary": summary,
        "filters": list_filter_options(events),
        "series": build_chart_series(events, max_points=chart_points),
        "compactions": compaction_timeline(events),
        "recent": recent_table_rows(events),
        "recommendations": recommendations(summary),
        "live_buffer_total": live_total,
        "telemetry_log": str(log_path or TELEMETRY_LOG_PATH),
    }
