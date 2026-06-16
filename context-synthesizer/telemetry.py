"""
Shared bifurcated token economics — cost math and JSONL event logging.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_live_lock = threading.Lock()
_live_events: list[dict[str, Any]] = []
_MAX_LIVE_EVENTS = int(os.environ.get("TELEMETRY_LIVE_BUFFER", "5000"))

# Sonnet 4.6 defaults (override via env for other models in future)
PRICE_UNCACHED = float(os.environ.get("PRICE_UNCACHED_INPUT", "3.00"))
PRICE_CACHE_READ = float(os.environ.get("PRICE_CACHE_READ", "0.30"))
PRICE_CACHE_WRITE = float(os.environ.get("PRICE_CACHE_WRITE", "3.75"))
PRICE_OUTPUT = float(os.environ.get("PRICE_OUTPUT", "15.00"))

DEFAULT_STATS_DIR = Path(__file__).resolve().parent / "stats"
TELEMETRY_LOG_PATH = Path(os.environ.get("TELEMETRY_LOG_PATH", str(DEFAULT_STATS_DIR / "telemetry.jsonl")))

# Anthropic minimum prefix size for prompt caching (Sonnet family)
MIN_CACHE_TOKENS = 1024
CHARS_PER_TOKEN_EST = 4


@dataclass
class UsageSnapshot:
    input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_input_tokens(self) -> int:
        return self.input_tokens + self.cache_read_input_tokens + self.cache_creation_input_tokens

    @classmethod
    def from_api(cls, usage: Any) -> UsageSnapshot:
        if usage is None:
            return cls()
        if isinstance(usage, dict):
            return cls(
                input_tokens=int(usage.get("input_tokens") or 0),
                cache_read_input_tokens=int(usage.get("cache_read_input_tokens") or 0),
                cache_creation_input_tokens=int(usage.get("cache_creation_input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
            )
        return cls(
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            cache_read_input_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            cache_creation_input_tokens=int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )


@dataclass
class CostSnapshot:
    actual_usd: float
    baseline_usd: float
    saved_usd: float
    savings_pct: float
    cache_efficiency_pct: float


def estimate_tokens(char_count: int) -> int:
    """Fast local estimate (~4 chars/token) for per-request context sizing."""
    return max(0, char_count // CHARS_PER_TOKEN_EST)


@dataclass
class ContextSnapshot:
    """Proxy payload shape at request time — tune compaction and cache layers."""

    layer1_chars: int = 0
    ledger_chars: int = 0
    layer3_chars: int = 0
    layer3_messages: int = 0
    prompt_chars: int = 0
    client_message_count: int = 0
    ignored_messages: int = 0
    naive_client_chars: int = 0
    # L2a — pinned checkpoints (@synth-remember:)
    pinned_checkpoints: int = 0
    checkpoint_chars: int = 0
    turn_number: int = 0
    lifetime_turn: int = 0
    turns_until_compaction: int = 0
    max_turns_threshold: int = 10
    max_layer3_turns: int = 10
    compaction_token_threshold: int = 0
    est_history_tokens: int = 0
    stream: bool = False
    max_tokens: int = 0

    @property
    def payload_chars(self) -> int:
        return (
            self.layer1_chars
            + self.checkpoint_chars
            + self.ledger_chars
            + self.layer3_chars
            + self.prompt_chars
        )

    @property
    def est_layer1_tokens(self) -> int:
        return estimate_tokens(self.layer1_chars)

    @property
    def est_checkpoint_tokens(self) -> int:
        return estimate_tokens(self.checkpoint_chars)

    @property
    def est_ledger_tokens(self) -> int:
        return estimate_tokens(self.ledger_chars)

    @property
    def est_layer3_tokens(self) -> int:
        return estimate_tokens(self.layer3_chars)

    @property
    def est_prompt_tokens(self) -> int:
        return estimate_tokens(self.prompt_chars)

    @property
    def est_payload_tokens(self) -> int:
        return estimate_tokens(self.payload_chars)

    @property
    def l1_cache_eligible_est(self) -> bool:
        return self.est_layer1_tokens >= MIN_CACHE_TOKENS

    @property
    def optimized_message_count(self) -> int:
        # L1 + L2a (if pins) + L2b + rolling turns + fresh user prompt
        has_pins = self.pinned_checkpoints > 0
        return 1 + (1 if has_pins else 0) + 1 + self.layer3_messages + 1

    @property
    def est_naive_tokens(self) -> int:
        """IDE full transcript size (what Claude Code sent, char est.)."""
        return estimate_tokens(self.naive_client_chars)

    @property
    def compression_vs_naive_pct(self) -> float:
        naive = self.est_naive_tokens
        shaped = self.est_payload_tokens
        if naive <= 0:
            return 0.0
        return max(0.0, (1.0 - shaped / naive) * 100.0)


@dataclass
class SynthesisMetrics:
    """Derived signals for tuning the synthesizer (thresholds, ledger size, cache)."""

    total_input_tokens: int = 0
    uncached_tail_tokens: int = 0
    uncached_tail_pct: float = 0.0
    cache_read_pct: float = 0.0
    cache_write_pct: float = 0.0
    output_to_input_ratio: float = 0.0
    client_bloat_ratio: float = 0.0
    est_uncached_vs_actual_delta: int = 0
    l1_cache_eligible_est: bool = False
    est_l3_l4_tokens: int = 0
    est_naive_tokens: int = 0
    est_shaped_tokens: int = 0
    compression_vs_naive_pct: float = 0.0

    @classmethod
    def from_usage_and_context(cls, usage: UsageSnapshot, context: ContextSnapshot) -> SynthesisMetrics:
        total_in = usage.total_input_tokens
        uncached_pct = (usage.input_tokens / total_in * 100.0) if total_in > 0 else 0.0
        read_pct = (usage.cache_read_input_tokens / total_in * 100.0) if total_in > 0 else 0.0
        write_pct = (usage.cache_creation_input_tokens / total_in * 100.0) if total_in > 0 else 0.0
        out_ratio = (usage.output_tokens / total_in) if total_in > 0 else 0.0
        opt_msgs = max(context.optimized_message_count, 1)
        bloat = context.client_message_count / opt_msgs if context.client_message_count else 0.0
        est_tail = context.est_layer3_tokens + context.est_prompt_tokens
        shaped = context.est_payload_tokens
        naive = context.est_naive_tokens
        return cls(
            total_input_tokens=total_in,
            uncached_tail_tokens=usage.input_tokens,
            uncached_tail_pct=uncached_pct,
            cache_read_pct=read_pct,
            cache_write_pct=write_pct,
            output_to_input_ratio=out_ratio,
            client_bloat_ratio=bloat,
            est_uncached_vs_actual_delta=usage.input_tokens - est_tail,
            l1_cache_eligible_est=context.l1_cache_eligible_est,
            est_l3_l4_tokens=est_tail,
            est_naive_tokens=naive,
            est_shaped_tokens=shaped,
            compression_vs_naive_pct=context.compression_vs_naive_pct,
        )


def compute_synthesis_metrics(usage: UsageSnapshot, context: ContextSnapshot) -> SynthesisMetrics:
    return SynthesisMetrics.from_usage_and_context(usage, context)


@dataclass
class TelemetryEvent:
    ts: str
    source: str  # "proxy" | "cli_import"
    developer_id: str
    session_id: str
    model: str
    latency_s: float | None
    usage: UsageSnapshot
    cost: CostSnapshot
    turn_number: int | None = None
    layer3_messages: int | None = None
    compaction_triggered: bool = False
    project_path: str | None = None
    client: str | None = None
    context: ContextSnapshot | None = None
    synthesis: SynthesisMetrics | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": self.ts,
            "source": self.source,
            "developer_id": self.developer_id,
            "session_id": self.session_id,
            "model": self.model,
            "latency_s": self.latency_s,
            "turn_number": self.turn_number,
            "layer3_messages": self.layer3_messages,
            "compaction_triggered": self.compaction_triggered,
            "project_path": self.project_path,
            "client": self.client,
            "usage": asdict(self.usage),
            "cost": asdict(self.cost),
            "extra": self.extra,
        }
        if self.context is not None:
            payload["context"] = {
                **{k: v for k, v in asdict(self.context).items()},
                "payload_chars": self.context.payload_chars,
                "est_layer1_tokens": self.context.est_layer1_tokens,
                "est_checkpoint_tokens": self.context.est_checkpoint_tokens,
                "est_ledger_tokens": self.context.est_ledger_tokens,
                "est_layer3_tokens": self.context.est_layer3_tokens,
                "est_prompt_tokens": self.context.est_prompt_tokens,
                "est_payload_tokens": self.context.est_payload_tokens,
                "est_naive_tokens": self.context.est_naive_tokens,
                "compression_vs_naive_pct": self.context.compression_vs_naive_pct,
                "l1_cache_eligible_est": self.context.l1_cache_eligible_est,
                "optimized_message_count": self.context.optimized_message_count,
            }
        if self.synthesis is not None:
            payload["synthesis"] = asdict(self.synthesis)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def compute_costs(usage: UsageSnapshot) -> CostSnapshot:
    actual = (
        (usage.input_tokens * PRICE_UNCACHED)
        + (usage.cache_read_input_tokens * PRICE_CACHE_READ)
        + (usage.cache_creation_input_tokens * PRICE_CACHE_WRITE)
        + (usage.output_tokens * PRICE_OUTPUT)
    ) / 1_000_000
    baseline = (
        (usage.total_input_tokens * PRICE_UNCACHED) + (usage.output_tokens * PRICE_OUTPUT)
    ) / 1_000_000
    saved = baseline - actual
    savings_pct = (saved / baseline * 100.0) if baseline > 0 else 0.0
    total_in = usage.total_input_tokens
    cache_eff = (usage.cache_read_input_tokens / total_in * 100.0) if total_in > 0 else 0.0
    return CostSnapshot(
        actual_usd=actual,
        baseline_usd=baseline,
        saved_usd=saved,
        savings_pct=savings_pct,
        cache_efficiency_pct=cache_eff,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def push_live_event(payload: dict[str, Any]) -> None:
    with _live_lock:
        _live_events.append(payload)
        if len(_live_events) > _MAX_LIVE_EVENTS:
            del _live_events[: len(_live_events) - _MAX_LIVE_EVENTS]


def get_live_events(*, since_index: int = 0) -> tuple[list[dict[str, Any]], int]:
    with _live_lock:
        total = len(_live_events)
        if since_index < 0:
            since_index = 0
        return list(_live_events[since_index:]), total


def append_event(event: TelemetryEvent, log_path: Path | None = None) -> None:
    payload = event.to_dict()
    push_live_event(payload)
    path = log_path or TELEMETRY_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def print_telemetry_report(
    usage: UsageSnapshot,
    cost: CostSnapshot,
    *,
    elapsed_time: float,
    session_id: str,
    developer_id: str,
    context: ContextSnapshot | None = None,
    synthesis: SynthesisMetrics | None = None,
) -> None:
    print("\n┌────────────────────────────────────────────────────────┐")
    print("│             CONTEXT ECONOMY BENCHMARK REPORT           │")
    print("├────────────────────────────────────────────────────────┤")
    print(f"│ Developer:          {developer_id[:40]:<40}")
    print(f"│ Session:            {session_id[:40]:<40}")
    print(f"│ Latency:            {elapsed_time:.2f} seconds")
    print(f"│ Uncached Inputs:    {usage.input_tokens:,} tokens")
    print(f"│ Cache Reads (Hits): {usage.cache_read_input_tokens:,} tokens (90% off!)")
    print(f"│ Cache Writes:       {usage.cache_creation_input_tokens:,} tokens")
    print(f"│ Generated Outputs:  {usage.output_tokens:,} tokens")
    if synthesis is not None:
        print("├────────────────────────────────────────────────────────┤")
        print(f"│ Uncached tail:      {synthesis.uncached_tail_pct:>6.1f}% of input")
        print(f"│ Cache read share:   {synthesis.cache_read_pct:>6.1f}% of input")
        print(f"│ Client bloat ratio: {synthesis.client_bloat_ratio:>6.1f}x msgs")
        if synthesis.est_naive_tokens > 0:
            print(
                f"│ Shaped vs naive:    {synthesis.est_shaped_tokens:,} / "
                f"{synthesis.est_naive_tokens:,} tok ({synthesis.compression_vs_naive_pct:.1f}% smaller)"
            )
    if context is not None:
        print("├────────────────────────────────────────────────────────┤")
        print(f"│ Est. L1/L2a/L2b/L3/L4: {context.est_layer1_tokens:,} / "
              f"{context.est_checkpoint_tokens:,} / {context.est_ledger_tokens:,} / "
              f"{context.est_layer3_tokens:,} / {context.est_prompt_tokens:,} tok")
        if context.pinned_checkpoints > 0:
            print(f"│ Pinned checkpoints: {context.pinned_checkpoints} "
                  f"({context.checkpoint_chars:,} chars, ~{context.est_checkpoint_tokens:,} tok)")
        print(f"│ L1 cache eligible:  {'yes' if context.l1_cache_eligible_est else 'NO':>6}")
        print(f"│ Turn {context.turn_number}/{context.max_turns_threshold} "
              f"(lifetime {context.lifetime_turn})")
    print("├────────────────────────────────────────────────────────┤")
    print(f"│ ACTUAL COST:        ${cost.actual_usd:.4f}")
    print(f"│ UNOPTIMIZED COST:   ${cost.baseline_usd:.4f}")
    print(f"│ REALIZED SAVINGS:   ${cost.saved_usd:.4f} ({cost.savings_pct:.1f}% Saved)")
    print(f"│ Cache Efficiency:   {cost.cache_efficiency_pct:.1f}%")
    print("└────────────────────────────────────────────────────────┘\n")
