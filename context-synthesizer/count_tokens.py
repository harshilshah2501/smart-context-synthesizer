#!/usr/bin/env python3
"""
Verify Claude.md token budget against the Layer 1 cache block structure.

Usage:
    .venv/bin/python context-synthesizer/count_tokens.py
    .venv/bin/python context-synthesizer/count_tokens.py --path context-synthesizer/Claude.md --target 200000
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from anthropic import Anthropic, NotFoundError

from models import AVAILABLE_MODELS, DEFAULT_CHAT_MODEL, MODEL_ROLES

DEFAULT_PATH = Path(__file__).resolve().parent / "Claude.md"
DEFAULT_MODEL = DEFAULT_CHAT_MODEL
DEFAULT_TARGET = 200_000
MIN_CACHE_TOKENS = 1024  # Anthropic minimum for prompt caching


def count_layer1_tokens(client: Anthropic, content: str, model: str) -> int:
    result = client.messages.count_tokens(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    )
    return result.input_tokens


def main() -> int:
    parser = argparse.ArgumentParser(description="Count Claude.md tokens for Layer 1 cache pinning.")
    parser.add_argument(
        "--path",
        default=os.environ.get("CLAUDE_MD_PATH", str(DEFAULT_PATH)),
        help="Path to Claude.md (default: context-synthesizer/Claude.md)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model used for token counting")
    parser.add_argument(
        "--target",
        type=int,
        default=DEFAULT_TARGET,
        help="Target token budget (default: 200,000)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print models available on your account and exit",
    )
    args = parser.parse_args()

    if args.list_models:
        print("Models on your account (from models.py registry):\n")
        for model_id in AVAILABLE_MODELS:
            role = MODEL_ROLES.get(model_id, "")
            print(f"  {model_id:<30} {role}")
        print(f"\nActive default (ANTHROPIC_MODEL): {DEFAULT_CHAT_MODEL}")
        return 0

    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 1

    content = path.read_text(encoding="utf-8")
    client = Anthropic()
    try:
        tokens = count_layer1_tokens(client, content, args.model)
    except NotFoundError:
        print(f"ERROR: Model not found: {args.model}\n", file=sys.stderr)
        print("Pick a model from your account. Examples:", file=sys.stderr)
        for model_id in AVAILABLE_MODELS[:5]:
            print(f"  --model {model_id}", file=sys.stderr)
        print("Run with --list-models for the full list.", file=sys.stderr)
        return 1

    pct_of_target = (tokens / args.target * 100) if args.target else 0
    cache_eligible = tokens >= MIN_CACHE_TOKENS

    print("┌────────────────────────────────────────────────────────┐")
    print("│              CLAUDE.MD TOKEN BUDGET REPORT             │")
    print("├────────────────────────────────────────────────────────┤")
    print(f"│ Path:               {str(path)[:40]:<40}")
    print(f"│ Model:              {args.model:<40}")
    print(f"│ Characters:         {len(content):>12,}{' ' * 27}")
    print(f"│ Layer 1 Tokens:     {tokens:>12,}{' ' * 27}")
    print(f"│ Target Budget:      {args.target:>12,}{' ' * 27}")
    print(f"│ % of Target:        {pct_of_target:>11.1f}%{' ' * 28}")
    print(f"│ Cache Eligible:      {'YES' if cache_eligible else 'NO':>12}{' ' * 27}")
    print("└────────────────────────────────────────────────────────┘")

    if tokens < MIN_CACHE_TOKENS:
        print(f"\n⚠ Below minimum cache threshold ({MIN_CACHE_TOKENS} tokens).")
    if tokens > args.target:
        print(f"\n⚠ Exceeds target budget by {tokens - args.target:,} tokens.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
