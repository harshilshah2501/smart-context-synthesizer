#!/usr/bin/env python3
"""
Assemble a production-sized Claude.md (Layer 1) from project documentation.

Teams replace the starter ~400-token file with their real architecture corpus (~200K tokens).
This script concatenates markdown sources into one cache-pinnable file.

Usage:
    .venv/bin/python context-synthesizer/build_production_claude_md.py
    .venv/bin/python context-synthesizer/build_production_claude_md.py \\
        --output context-synthesizer/Claude.production.md \\
        --source context-synthesizer/README.md \\
        --source ../context_os_technical_report.md

Then verify:
    CLAUDE_MD_PATH=context-synthesizer/Claude.production.md \\
        .venv/bin/python context-synthesizer/count_tokens.py
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from telemetry import CHARS_PER_TOKEN_EST, MIN_CACHE_TOKENS, estimate_tokens

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
DEFAULT_OUTPUT = ROOT / "Claude.production.md"

DEFAULT_SOURCES = [
    ROOT / "Claude.md",
    ROOT / "README.md",
    REPO_ROOT / "docs" / "reports" / "SYNTHESIZER_RND_REPORT.md",
    REPO_ROOT / "docs" / "reports" / "BENCHMARK_ANALYSIS.md",
    REPO_ROOT / "docs" / "guides" / "Usage.md",
    REPO_ROOT / "docs" / "context_os_technical_report.md",
]


def _section(path: Path, content: str) -> str:
    rel = path.resolve()
    digest = hashlib.sha256(content.encode()).hexdigest()[:12]
    header = f"\n\n<!-- SOURCE: {rel} sha256:{digest} -->\n\n"
    return f"# {path.name}\n\n{content.strip()}{header}"


def build(sources: list[Path]) -> str:
    parts = [
        "# Production Context — Layer 1 (cache-pinned)\n",
        "Byte-identical across requests. Do not inject dynamic values here.\n",
    ]
    for path in sources:
        if not path.is_file():
            raise FileNotFoundError(f"Source not found: {path}")
        parts.append(_section(path, path.read_text(encoding="utf-8")))
    return "\n".join(parts).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build production Claude.md from markdown sources.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        type=Path,
        help="Markdown file to include (repeatable). Defaults to bundled project docs.",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=MIN_CACHE_TOKENS,
        help=f"Warn if estimate is below this (default: {MIN_CACHE_TOKENS})",
    )
    args = parser.parse_args()

    sources = args.sources if args.sources else DEFAULT_SOURCES
    body = build(sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body, encoding="utf-8")

    est = estimate_tokens(len(body))
    print(f"Wrote {args.output} ({len(body):,} chars, ~{est:,} tokens est.)")
    print(f"Sources: {len(sources)} file(s)")
    if est < args.min_tokens:
        print(
            f"\n⚠ Below {args.min_tokens:,} token minimum for prompt caching. "
            "Add your team's architecture docs via --source."
        )
        return 1
    print(f"\nNext: CLAUDE_MD_PATH={args.output} .venv/bin/python context-synthesizer/count_tokens.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
