#!/usr/bin/env python3
"""
Compare naive context vs Dreaming v4 preprocessing / compaction at a spike turn.

Replays a Claude CLI transcript up to --turn (default 178 on ac4ecef7), then shows:
  1. Naive cumulative history (counterfactual full transcript)
  2. Preprocessed sliding window (v4 bash collapse + read dedup, no LLM)
  3. Synthesizer-shaped payload (ledger + layer3 + current user)
  4. Optional: real Dreaming v4 ledger via Haiku (--run-dreaming)

Usage:
    .venv/bin/python context-synthesizer/compare_compaction.py \\
        --cli-root context-synthesizer/stats/backups/meet-chavda/.claude/projects \\
        --session ac4ecef7 --turn 178

    export ANTHROPIC_API_KEY=...
    export COMPACTION_MODEL=claude-haiku-4-5-20251001   # Haiku for dreaming (default)

    .venv/bin/python context-synthesizer/compare_compaction.py \\
        --session ac4ecef7 --turn 178 --run-dreaming --dreaming-batches 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import claude_parse as claude_mod
from compaction import build_compaction_prompt, format_turns_for_compaction
from telemetry import estimate_tokens

INITIAL_LEDGER = "Initial State: System active and optimized."
DEFAULT_CLI_ROOT = claude_mod.DEFAULT_CLI_ROOT
HAIKU_COMPACTION_MODEL = "claude-haiku-4-5-20251001"
SYNTH_DIR = Path(__file__).resolve().parent


def load_local_env() -> None:
    """Load KEY=VALUE lines from .env files without overwriting existing env."""
    for path in (
        SYNTH_DIR / ".env",
        SYNTH_DIR.parent / ".env",
        Path.home() / ".anthropic_api_key",
    ):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def resolve_compaction_model(explicit: str | None, *, force_haiku: bool) -> str:
    if force_haiku:
        return HAIKU_COMPACTION_MODEL
    if explicit:
        return explicit
    return os.environ.get("COMPACTION_MODEL", HAIKU_COMPACTION_MODEL)


@dataclass
class TurnBundle:
    turn: int
    user_text: str
    assistant_text: str
    tool_calls: int = 0
    files_touched: list[str] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return len(self.user_text) + len(self.assistant_text)


def _content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            parts.append(block.get("text") or "")
        elif kind == "tool_use":
            name = block.get("name") or "tool"
            inp = block.get("input")
            parts.append(f"[ToolUse {name}]\n{json.dumps(inp, indent=2) if inp else ''}")
        elif kind == "tool_result":
            parts.append(f"[ToolResult]\n{block.get('content') or ''}")
    return "\n".join(p for p in parts if p)


def extract_turns(path: Path) -> list[TurnBundle]:
    lines = [
        json.loads(ln)
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip()
    ]
    turns: list[TurnBundle] = []
    i = 0
    turn_idx = 0

    while i < len(lines):
        record = lines[i]
        if record.get("type") == "system" and record.get("subtype") == "compact_boundary":
            i += 1
            continue
        if not claude_mod.is_human_user(record):
            i += 1
            continue

        turn_idx += 1
        user_text = _content_to_text((record.get("message") or {}).get("content"))
        assistant_parts: list[str] = []
        tool_calls = 0
        files: list[str] = []

        i += 1
        while i < len(lines):
            rec = lines[i]
            if rec.get("type") == "system" and rec.get("subtype") == "compact_boundary":
                i += 1
                continue
            if claude_mod.is_human_user(rec):
                break
            if rec.get("type") == "assistant":
                msg = rec.get("message") or {}
                assistant_parts.append(_content_to_text(msg.get("content")))
                _, n_tools, tool_list, paths = claude_mod.parse_assistant_blocks(rec)
                tool_calls += n_tools
                files.extend(paths)
                for name, inp in tool_list:
                    for p in claude_mod.paths_from_tool_input(inp):
                        files.append(p)
            elif rec.get("type") == "user":
                assistant_parts.append(_content_to_text((rec.get("message") or {}).get("content")))
            i += 1

        turns.append(
            TurnBundle(
                turn=turn_idx,
                user_text=user_text.strip(),
                assistant_text="\n\n".join(p for p in assistant_parts if p).strip(),
                tool_calls=tool_calls,
                files_touched=sorted(set(files)),
            )
        )
    return turns


def turns_to_messages(turns: list[TurnBundle]) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for t in turns:
        if t.user_text:
            msgs.append({"role": "user", "content": t.user_text})
        if t.assistant_text:
            msgs.append({"role": "assistant", "content": t.assistant_text})
    return msgs


def naive_cumulative_text(turns: list[TurnBundle], through_turn: int) -> str:
    chunks: list[str] = []
    for t in turns:
        if t.turn > through_turn:
            break
        chunks.append(f"=== Turn {t.turn} USER ===\n{t.user_text}")
        if t.assistant_text:
            chunks.append(f"=== Turn {t.turn} ASSISTANT/TOOLS ===\n{t.assistant_text}")
    return "\n\n".join(chunks)


def preprocessed_window_text(turns: list[TurnBundle], through_turn: int, window: int) -> str:
    slice_turns = [t for t in turns if through_turn - window < t.turn <= through_turn]
    return format_turns_for_compaction(turns_to_messages(slice_turns), lambda x: x)


def synth_shaped_text(
    *,
    layer1_chars: int,
    ledger_text: str,
    turns: list[TurnBundle],
    through_turn: int,
    window: int,
) -> str:
    current = next(t for t in turns if t.turn == through_turn)
    layer3 = preprocessed_window_text(turns, through_turn - 1, window) if through_turn > 1 else ""
    parts = [
        f"=== LAYER 1 ({layer1_chars:,} chars est.) ===",
        "(Claude.md — omitted in replay)",
        f"=== LAYER 2 LEDGER ({len(ledger_text):,} chars) ===",
        ledger_text,
        f"=== LAYER 3 WINDOW (turns {max(1, through_turn - window)}–{through_turn - 1}) ===",
        layer3,
        f"=== LAYER 4 CURRENT USER (turn {through_turn}) ===",
        current.user_text,
    ]
    return "\n\n".join(parts)


def _preview(label: str, text: str, *, max_chars: int = 3500) -> None:
    print(f"\n{'─' * 72}")
    print(f"  {label}")
    print(f"{'─' * 72}")
    if not text.strip():
        print("  (empty)")
        return
    if len(text) <= max_chars:
        print(textwrap.indent(text, "  "))
    else:
        head = text[: max_chars // 2]
        tail = text[-max_chars // 4 :]
        omitted = len(text) - len(head) - len(tail)
        print(textwrap.indent(head, "  "))
        print(f"\n  … [{omitted:,} chars omitted] …\n")
        print(textwrap.indent(tail, "  "))


def _stat_row(name: str, chars: int) -> str:
    tok = estimate_tokens(chars)
    return f"  {name:<28} {chars:>10,} chars  ~{tok:>8,} tok"


def dream_compact_sync(
    ledger: str,
    turns: list[TurnBundle],
    *,
    api_key: str,
    model: str,
) -> str:
    from anthropic import Anthropic

    turns_text = format_turns_for_compaction(turns_to_messages(turns), lambda x: x)
    prompt = build_compaction_prompt(ledger, turns_text)
    client = Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise RuntimeError(
            f"Compaction API call failed (model={model!r}). "
            f"Use --haiku or COMPACTION_MODEL={HAIKU_COMPACTION_MODEL}. "
            f"Original error: {exc}"
        ) from exc
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    new_ledger = "".join(parts).strip()
    return new_ledger or ledger


def replay_ledger(
    turns: list[TurnBundle],
    through_turn: int,
    *,
    window: int,
    api_key: str,
    model: str,
    max_batches: int | None = None,
) -> tuple[str, int]:
    """Simulate proxy compaction every `window` turns up to (not including) through_turn."""
    ledger = INITIAL_LEDGER
    prior = [t for t in turns if t.turn < through_turn]
    batches_run = 0
    for start in range(0, len(prior), window):
        batch = prior[start : start + window]
        if not batch:
            break
        if max_batches is not None and batches_run >= max_batches:
            break
        print(
            f"  [dreaming] compacting turns {batch[0].turn}–{batch[-1].turn} "
            f"({len(batch)} turns, ledger {len(ledger):,} chars)…"
        )
        ledger = dream_compact_sync(ledger, batch, api_key=api_key, model=model)
        batches_run += 1
        print(f"             → ledger now {len(ledger):,} chars (~{estimate_tokens(len(ledger)):,} tok)")
    return ledger, batches_run


def print_comparison_report(
    *,
    turns: list[TurnBundle],
    through_turn: int,
    window: int,
    layer1_chars: int,
    ledger_text: str,
    run_dreaming: bool,
    show_previews: bool,
    export_path: Path | None,
) -> dict[str, Any]:
    target = next((t for t in turns if t.turn == through_turn), None)
    if not target:
        raise ValueError(f"Turn {through_turn} not found (session has {len(turns)} turns)")

    naive = naive_cumulative_text(turns, through_turn)
    raw_window_turns = [t for t in turns if through_turn - window < t.turn <= through_turn]
    raw_window = naive_cumulative_text(raw_window_turns, through_turn)
    prep_window = preprocessed_window_text(turns, through_turn, window)
    synth = synth_shaped_text(
        layer1_chars=layer1_chars,
        ledger_text=ledger_text,
        turns=turns,
        through_turn=through_turn,
        window=window,
    )

    layer3_chars = len(preprocessed_window_text(turns, through_turn - 1, window)) if through_turn > 1 else 0
    synth_chars = layer1_chars + len(ledger_text) + layer3_chars + len(target.user_text)

    prep_saved = 1.0 - (len(prep_window) / len(raw_window)) if raw_window else 0.0
    synth_saved = 1.0 - (synth_chars / len(naive)) if naive else 0.0

    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║           COMPACTION COMPARE — naive vs Dreaming v4                  ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Turn:        {through_turn:<56}║")
    print(f"║ Window:      {window} turns{' ' * 51}║")
    print(f"║ Spike turn:  {target.tool_calls} tool calls, {target.total_chars:,} chars this turn{' ' * 18}║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║ SIZE COMPARISON                                                      ║")
    print(_stat_row("Naive (turns 1–{})".format(through_turn), len(naive)))
    print(_stat_row(f"Raw window ({window} turns)", len(raw_window)))
    print(_stat_row("Preprocessed window (v4)", len(prep_window)))
    print(_stat_row("Ledger (replay)", len(ledger_text)))
    print(_stat_row("Synthesizer-shaped payload", synth_chars))
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║ Prep-only save (window):     {prep_saved * 100:>6.1f}%{' ' * 36}║")
    print(f"║ Synth-shaped save (total):   {synth_saved * 100:>6.1f}%{' ' * 36}║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    if show_previews:
        _preview("NAIVE — last 2 turns of cumulative history", _tail_turns(naive, 2))
        _preview("RAW WINDOW — turns around spike (unprocessed)", raw_window)
        _preview("PREPROCESSED WINDOW — v4 bash collapse + read dedup (no LLM)", prep_window)
        _preview("LEDGER after replay", ledger_text)
        _preview("SYNTHESIZER-SHAPED PAYLOAD (ledger + window + user)", synth)

    result = {
        "turn": through_turn,
        "window": window,
        "tool_calls_at_turn": target.tool_calls,
        "chars": {
            "naive_cumulative": len(naive),
            "raw_window": len(raw_window),
            "preprocessed_window": len(prep_window),
            "ledger": len(ledger_text),
            "synthesizer_shaped": synth_chars,
        },
        "tokens_est": {
            "naive_cumulative": estimate_tokens(len(naive)),
            "preprocessed_window": estimate_tokens(len(prep_window)),
            "synthesizer_shaped": estimate_tokens(synth_chars),
        },
        "savings_pct": {
            "prep_window_vs_raw": round(prep_saved * 100, 1),
            "synth_shaped_vs_naive": round(synth_saved * 100, 1),
        },
        "ledger_text": ledger_text,
        "preprocessed_window": prep_window,
    }

    if export_path:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nExported → {export_path}")

    return result


def _tail_turns(text: str, n_turns: int) -> str:
    marker = "=== Turn "
    indices = [i for i in range(len(text)) if text.startswith(marker, i)]
    if len(indices) <= n_turns:
        return text
    return text[indices[-n_turns] :]


def main() -> int:
    load_local_env()

    parser = argparse.ArgumentParser(description="Compare naive vs Dreaming v4 at a spike turn.")
    parser.add_argument("--cli-root", type=Path, default=DEFAULT_CLI_ROOT)
    parser.add_argument("--session", default="ac4ecef7", help="Session id prefix")
    parser.add_argument("--turn", type=int, default=178, help="Spike turn to analyze")
    parser.add_argument("--window", type=int, default=int(os.environ.get("MAX_TURNS_THRESHOLD", "10")))
    parser.add_argument("--layer1-chars", type=int, default=0)
    parser.add_argument(
        "--run-dreaming",
        action="store_true",
        help="Call Haiku to build ledger (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--dreaming-batches",
        type=int,
        default=None,
        help="Limit compaction batches (default: all turns before --turn)",
    )
    parser.add_argument(
        "--compaction-model",
        default=None,
        help=f"Dreaming model (default: COMPACTION_MODEL env or {HAIKU_COMPACTION_MODEL})",
    )
    parser.add_argument(
        "--haiku",
        action="store_true",
        help=f"Force Haiku for compaction ({HAIKU_COMPACTION_MODEL})",
    )
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--export", type=Path, default=Path(__file__).resolve().parent / "stats" / "compare_compaction.json")
    args = parser.parse_args()

    path = claude_mod.find_transcript(
        args.cli_root,
        session_id=args.session,
        project=None,
        pick_largest=not args.session,
    )
    if not path:
        print(f"ERROR: session not found under {args.cli_root}", file=sys.stderr)
        return 1

    layer1 = args.layer1_chars
    if layer1 <= 0:
        claude_md = Path(__file__).resolve().parent / "Claude.md"
        layer1 = len(claude_md.read_text(encoding="utf-8")) if claude_md.is_file() else 0

    compaction_model = resolve_compaction_model(args.compaction_model, force_haiku=args.haiku)

    turns = extract_turns(path)
    print(f"Loaded {len(turns)} turns from {path.name}")
    print(f"Compaction model: {compaction_model}")

    ledger = INITIAL_LEDGER
    if args.run_dreaming:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            print(
                "ERROR: --run-dreaming requires ANTHROPIC_API_KEY\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n"
                "  or add it to context-synthesizer/.env",
                file=sys.stderr,
            )
            return 1
        if "haiku" not in compaction_model.lower():
            print(
                f"WARN: compaction model {compaction_model!r} is not Haiku — "
                f"pass --haiku for cheap/fast dreaming.",
                file=sys.stderr,
            )
        print(f"\nReplaying Dreaming v4 compaction ({compaction_model})…")
        try:
            ledger, n_batches = replay_ledger(
                turns,
                args.turn,
                window=args.window,
                api_key=api_key,
                model=compaction_model,
                max_batches=args.dreaming_batches,
            )
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Completed {n_batches} compaction batch(es).\n")
    else:
        print(
            "\nOffline mode (no API). Ledger = placeholder; prep window shows v4 preprocessing only."
        )
        print("Pass --run-dreaming with ANTHROPIC_API_KEY for real Haiku ledger.\n")

    print_comparison_report(
        turns=turns,
        through_turn=args.turn,
        window=args.window,
        layer1_chars=layer1,
        ledger_text=ledger,
        run_dreaming=args.run_dreaming,
        show_previews=not args.no_preview,
        export_path=args.export,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
