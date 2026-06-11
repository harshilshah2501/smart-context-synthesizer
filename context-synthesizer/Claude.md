# Project Context — Out-of-Bound Chronicles

This file is pinned at **messages[0]** with `cache_control: ephemeral`. It must remain
byte-identical across every proxy request to maximize Anthropic prompt-cache hits.

## Architecture

- **proxy_tool.py** — FastAPI gateway on `localhost:8080/v1/messages`
- **test_simulator.py** — 12-turn JetBrains client benchmark
- **count_tokens.py** — verifies this file fits the token budget

## Index-Aligned Payload Layers

| Layer | Index | Content | Cached |
|-------|-------|---------|--------|
| 1 | 0 | This Claude.md file | Yes |
| 2 | 1 | History Ledger synthesis | Yes |
| 3 | 2..N-1 | Sliding recent turns | No |
| 4 | N | Fresh user prompt | No |

## Engineering Rules

1. Never inject timestamps, UUIDs, or session metadata before Layer 2's cache breakpoint.
2. Ignore JetBrains' cumulative message history; extract only the latest user turn.
3. Normalize content blocks (string or array) before assembly.
4. Run background compaction ("dreaming") when turn threshold is met.
5. Scope session state via `X-Session-Id` request header.

## Code Style

- Python 3.12+, FastAPI, AsyncAnthropic SDK
- Minimal diffs; match existing conventions
- Telemetry: bifurcated cache read / write / uncached metrics

## Token Budget Note

Replace this starter file with your full ~200K-token rules corpus for production.
Run `count_tokens.py` to verify the budget before deployment.
