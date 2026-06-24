# Production Context — Layer 1 (cache-pinned)

> **Note:** Large benchmark / rules document used as Layer-1 cache content in internal
> studies. Review for org-specific names before publishing; safe to replace with your
> own `Claude.md` for production use.

Byte-identical across requests. Do not inject dynamic values here.

# Claude.md

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

<!-- SOURCE: /home/harshil/Out-of-bound-chronicles/context-synthesizer/Claude.md sha256:e1b3c0df6548 -->


# README.md

# Context Synthesizer

Offline analysis and tuning toolkit for **smart context compaction** — study long IDE sessions, estimate synthesizer-shaped payloads, and tune Dreaming rules. Built from real Claude Code and Cursor session logs.

The repo also contains `proxy_tool.py` (four-layer gateway + Dreaming) as the **implementation target** the synthesizer optimizes toward. The team does **not** route live traffic through it.

**Docs:**

| Doc | Read when |
|-----|-----------|
| **[Usage.md](Usage.md)** | Per-mode setup ([A / C / D](#data-collection-modes)) |
| **[SYNTHESIZER_RND_REPORT.md](SYNTHESIZER_RND_REPORT.md)** | Corpus analysis, caching findings, roadmap |
| [Technical report](../context_os_technical_report.md) | Gateway design, OS analogy, `proxy_tool.py` internals |
| [BENCHMARK_ANALYSIS.md](BENCHMARK_ANALYSIS.md) | Internal proxy benchmark (not a team workflow) |
| [CLI_STATS_GUIDE.md](CLI_STATS_GUIDE.md) | Mode A import details |

---

## Data collection modes

Three ways to gather session data. All are **offline** — read logs from disk, no API key, no proxy.

| Mode | Who | Data source | Tool |
|------|-----|-------------|------|
| **A** | Default — any Claude Code user | `~/.claude/projects/<project>/<session>.jsonl` | `import_cli_logs.py` |
| **C** | Cursor IDE | `~/.cursor/projects/.../agent-transcripts/` | `import_cursor_sessions.py` |
| **D** | Claude Max / Pro | Same paths as A, richer session analysis | `import_claude_sessions.py` |

| | Mode A | Mode D |
|--|--------|--------|
| **Use when** | Quick per-turn token import | Full corpus R&D (compression est., file re-reads, hot sessions) |
| **Token `usage`** | Yes (assistant turns) | Yes + session-level aggregates |
| **Synthesizer counterfactual** | No | Yes |

**Claude Max team → Mode D.** **Cursor team → Mode C.** **Simple weekly export → Mode A.**

JSONL `source` tags written by importers: `cli_import` (A), `claude_corpus` (D), `cursor_import` (C).

Setup: **[Usage.md](Usage.md)**

---

## Quick start

```bash
cd ~/Out-of-bound-chronicles

# Mode D — Claude Max (recommended)
.venv/bin/python context-synthesizer/import_claude_sessions.py \
  --developer "$(whoami)" --min-turns 25 --export stats/team.csv
.venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --largest

# Mode C — Cursor
.venv/bin/python context-synthesizer/import_cursor_sessions.py --project my-repo --min-turns 25
.venv/bin/python context-synthesizer/analyze_hot_session.py --source cursor --project my-repo --largest

# Mode A — quick Claude CLI import
.venv/bin/python context-synthesizer/import_cli_logs.py \
  --output context-synthesizer/stats/baseline.jsonl

# Team rollup
.venv/bin/python context-synthesizer/collect_stats.py --logs context-synthesizer/stats/
```

---

## What the synthesizer optimizes (target architecture)

When deployed via a gateway, the payload is four layers:

```
Layer 1  messages[0]   Claude.md              cache_control ✓
Layer 2  messages[1]   History ledger         cache_control ✓
Layer 3  messages[2..]  Rolling turns (≤10)    uncached
Layer 4  messages[N]    Latest user prompt     uncached
```

Implemented in `proxy_tool.py` with Dreaming v4 compaction (`compaction.py`). Modes A/C/D measure how much smaller this shape is vs native full history. See [technical report](../context_os_technical_report.md).

---

## Shipped vs. planned (summary)

| Shipped | Planned |
|---------|---------|
| Mode A/C/D import pipeline | `import_claude_backup.sh` one-shot import |
| Dreaming v4 + token/turn triggers in `proxy_tool.py` | Full ~200K production `Claude.md` |
| Hot session + caching analyzers | Phase 2 corpus regression suite |
| `build_production_claude_md.py` | |

---

## Repository files

| File | Mode | Purpose |
|------|------|---------|
| `import_cli_logs.py` | **A** | Import Claude CLI assistant turns + `usage` |
| `import_claude_sessions.py` | **D** | Full Claude corpus + compression estimates |
| `import_cursor_sessions.py` | **C** | Cursor transcript corpus |
| `analyze_hot_session.py` | D/C | Deep-dive one long session |
| `analyze_claude_caching.py` | D | Native Claude Code cache behavior |
| `collect_stats.py` | All | Team aggregate + tuning insights |
| `proxy_tool.py` | — | Gateway implementation (not team workflow) |
| `compaction.py` | — | Dreaming v4 prompt + turn prep |
| `telemetry.py` | — | Cost bifurcation math |
| `stats/` | — | Corpus JSONL output (gitignored) |

---

## Tuning signals (from corpus)

`collect_stats.py` aggregates all JSONL under `stats/` and prints a **corpus insights** block
(compression estimates from Mode D/C) plus token bifurcation from Mode A/D.

After import, look for:

| Signal | Healthy | Action if bad |
|--------|---------|---------------|
| Compression est. (Mode D) | ≥90% on 100+ turn sessions | Tighten Dreaming rules; check file re-reads |
| `cache_read` % in Claude logs | High on warm turns | Native caching works; focus on payload size |
| File re-reads (hot session) | Low | Ledger should keep latest file state only |
| Growth spikes | Rare | Token-based compaction trigger |

Full findings: [SYNTHESIZER_RND_REPORT.md](SYNTHESIZER_RND_REPORT.md).

<!-- SOURCE: /home/harshil/Out-of-bound-chronicles/context-synthesizer/README.md sha256:b6f90a2eb690 -->


# SYNTHESIZER_RND_REPORT.md

# Context Synthesizer — R&D Report

**Date:** 2026-06-10 (updated 2026-06-11)  
**Status:** Phase 1 complete — Phase 2 (corpus validation) next  
**Audience:** Team leads, infrastructure engineers, future maintainers  

This document captures the full arc of the Context Synthesizer project: goals, architecture, data-collection strategy, empirical findings from real developer sessions, and the strategic conclusion that **optimization lives in history shape—not in enabling prompt caching**.

**Companion docs:**

| Doc | Contents |
|-----|----------|
| [README.md](README.md) | Quick start, env vars, file index |
| [Usage.md](Usage.md) | Developer setup (Mode C/D primary) |
| [BENCHMARK_ANALYSIS.md](BENCHMARK_ANALYSIS.md) | 12-turn proxy simulator, cost bifurcation |
| [CLI_STATS_GUIDE.md](CLI_STATS_GUIDE.md) | Mode A import details |
| [context_os_technical_report.md](../context_os_technical_report.md) | Design rationale, OS analogy, shipped vs planned |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution: Four-Layer Gateway](#3-solution-four-layer-gateway)
4. [Project Evolution](#4-project-evolution)
5. [Data Collection Modes](#5-data-collection-modes)
6. [Proxy Benchmark (12-Turn Simulator)](#6-proxy-benchmark-12-turn-simulator)
7. [Developer Corpus: meet-chavda](#7-developer-corpus-meet-chavda)
8. [Native Claude Code Caching Analysis](#8-native-claude-code-caching-analysis)
9. [Hot Session Deep Dive: ac4ecef7](#9-hot-session-deep-dive-ac4ecef7)
10. [Cursor Corpus (m-coder)](#10-cursor-corpus-m-coder)
11. [Strategic Conclusion: Where Optimization Lives](#11-strategic-conclusion-where-optimization-lives)
12. [Economics Worked Example](#12-economics-worked-example)
13. [Telemetry & Tuning Signals](#13-telemetry--tuning-signals)
14. [Bugs Fixed During Analysis](#14-bugs-fixed-during-analysis)
15. [Shipped vs Planned](#15-shipped-vs-planned)
16. [Next Steps: Implement, Test, Deploy](#16-next-steps-implement-test-deploy)
17. [Repository Reference](#17-repository-reference)
18. [Glossary](#18-glossary)

---

## 1. Executive Summary

The **Context Synthesizer** is an offline R&D toolkit for **smart context compaction**. It imports long IDE sessions (Modes **A**, **C**, **D**), measures native token usage and history bloat, and estimates how much smaller a **four-layer gateway payload** would be. The gateway itself lives in `proxy_tool.py` (implementation target, not used in the team workflow).

**Key finding from real developer data (meet-chavda, 32 sessions, 859 turns):**

| Metric | Native Claude Code | Synthesizer opportunity |
|--------|-------------------|-------------------------|
| Cache read rate (warm turns) | **~99%** on assistant messages | Already solved — not our lever |
| Hot-session input prefix (turn 415) | **541K tokens** cumulative | Counterfactual **~23K** shaped payload (**97.5%** char reduction) |
| Cache writes per long session | **407 turns** with `cache_write` | Smaller, stabler prefix → fewer write spikes |
| File re-reads | `Admin.tsx` read **21×** | Code-aware ledger keeps latest state only |
| Tool bloat | **684 Bash**, **280 Read** calls | Collapse tool output in ledger |

**Bottom line:** Claude Code already caches brilliantly. Our value is as a **history architect**—shrinking and stabilizing what gets cached—not as a caching enabler.

**Team workflow:** Offline corpus only — **Mode D** (Claude Max), **Mode C** (Cursor), or **Mode A** (default Claude Code import). No live proxy, no API key.

---

## 2. Problem Statement

### The Context Tax

LLMs are stateless. Every API call must re-send prior context. In a long debugging session on a large codebase:

```
Component                    | Token count (illustrative)
-----------------------------|-------------
Claude.md (architecture)     | 200,000
Chat history (N turns)       | grows linearly
Current prompt               |   5,000
```

By turn 15+, input can exceed 350K tokens **per request**—mostly repeated background knowledge and verbatim tool output.

### Financial impact

At Sonnet 4.6 uncached input ($3.00/M):

```
50 turns × ~355K avg input ≈ 17.75M tokens → ~$53/session (naive)
```

Prompt caching reduces cost on the **stable prefix** (90% discount on `cache_read`). But if the prefix itself grows to 500K+ tokens, even discounted reads add up—and `cache_write` events on prefix growth are expensive.

---

## 3. Solution: Four-Layer Gateway

The proxy **ignores** the IDE’s cumulative message history except the latest user turn. It rebuilds payload from proxy-owned session state:

```
Layer 1  messages[0]   Claude.md              cache_control ✓  (stable, byte-identical)
Layer 2  messages[1]   History ledger         cache_control ✓  (mutated by compaction only)
Layer 3  messages[2..]  Rolling turns (≤10)    uncached
Layer 4  messages[N]    Latest user prompt     uncached
```

### OS analogy

| OS concept | Synthesizer layer |
|------------|-------------------|
| Page cache (stable, reusable) | Layer 1 + Layer 2 |
| Working RAM (sliding window) | Layer 3 |
| Swap / GC (background synthesis) | Dreaming compaction → ledger |

### Dreaming (compaction)

When `turn_number % MAX_TURNS_THRESHOLD == 0` (default **10**), a background Haiku call (`COMPACTION_MODEL`) synthesizes rolling turns into the history ledger, then clears the rolling window. Ledger mutation is the only intentional cache-bust on Layer 2.

### Ecosystem position

```
JetBrains / Claude CLI → [rtk-ai/rtk] → Context Synthesizer → Anthropic → [claude-devtools]
```

| Tool | Role |
|------|------|
| `rtk-ai/rtk` | Compress terminal output before it enters context |
| **Context Synthesizer** | Structure API payload, cache `Claude.md`, compact history |
| `claude-devtools` | Visualize session logs after the fact |

---

## 4. Project Evolution

| Phase | Decision |
|-------|----------|
| **Initial goal** | Ubuntu `.deb` for JetBrains team with shared API gateway |
| **Pivot** | Team uses **Claude Max subscription**, not BYOK — live proxy not viable for most devs |
| **Dropped** | **Ubuntu `.deb` rollout** — no team-wide package install; `packaging/` kept as unused legacy |
| **Revised goal** | Build a **smart, code-aware synthesizer** using offline session analysis |
| **Vendor-agnostic gateway** | Discussed and **de-prioritized** — focus is synthesizer R&D, not multi-vendor routing |
| **Cursor support** | Live proxy not possible; **Mode C** imports `~/.cursor/projects/**/agent-transcripts/` |
| **Delivery today** | Python scripts + venv; weekly corpus export (Modes A / C / D) |

---

## 5. Data Collection Modes

| Mode | Source | API key? | Token bifurcation | Primary use |
|------|--------|----------|-------------------|-------------|
| **A** | `import_cli_logs.py` — Claude CLI assistant turns | No | Yes (per turn) | Default weekly token snapshot |
| **C** | `import_cursor_sessions.py` — Cursor transcripts | No | Estimates only | Cursor long-session R&D |
| **D** | `import_claude_sessions.py` — `~/.claude/projects/` | No | **Yes** + session aggregates | **Claude Max / Pro synthesizer R&D** |

### Why three offline modes

Claude Max and Cursor do not expose a local API hook for live gateway interception. All analysis reads **locally stored JSONL** after the fact. Mode D adds synthesizer counterfactuals and hot-session tooling on top of the same paths Mode A uses.

### Weekly developer workflow (Mode D)

```bash
.venv/bin/python context-synthesizer/import_claude_sessions.py \
  --developer your-handle --min-turns 25 \
  --export stats/$(whoami)_claude.csv

.venv/bin/python context-synthesizer/analyze_hot_session.py \
  --source claude --largest --export stats/hot_session.json
```

### Team lead aggregation

```bash
.venv/bin/python context-synthesizer/collect_stats.py \
  --logs context-synthesizer/stats/ --group-by developer_id
```

### Synthesizer-shaped counterfactual (offline)

For each turn, parsers compute:

- **Naive:** cumulative chars of all user + assistant + tool content (what full history would weigh)
- **Synthesizer est:** `layer1_chars + ledger_chars + layer3_window + current_user_chars`

Defaults: `layer1_chars=0` (or production ~800K for 200K tokens), `ledger_chars=2000`, `max_turns=10`.

```text
compression_ratio = 1 - (synth_chars / naive_chars)
```

This estimates **payload shape benefit** independent of live proxy deployment.

---

## 6. Proxy Benchmark (12-Turn Simulator)

**Run:** 2026-06-10 · `test_simulator.py` · `claude-sonnet-4-6` · starter `Claude.md` (~380 tokens)

| Metric | Value |
|--------|------:|
| Wall time | 200.31 s |
| Uncached input | 22,715 tokens |
| Cache read | 16,202 tokens |
| Cache write | 15,755 tokens |
| Output | 10,010 tokens |
| Baseline cost | $0.3142 |
| Realized cost | $0.2822 |
| **Savings** | **10.2%** |
| Cache efficiency | 29.6% |

### Why only 10.2% (not ~90%)

Starter `Claude.md` is **below Sonnet 4.6’s 1,024-token minimum** per `cache_control` block. Cache-eligible prefix was ~2.5K tokens, not 200K. Uncached Layer 3+4 dominated spend.

**Conclusion:** Proxy layout behaved correctly (cache engaged turn 4+, reads climbed turns 6–10, compaction at turn 10, cache bust on turn 11 massive prompt). **The bifurcation works; the corpus is not production-sized.**

Full turn-by-turn narrative: [BENCHMARK_ANALYSIS.md](BENCHMARK_ANALYSIS.md).

---

## 7. Developer Corpus: meet-chavda

**Source:** `context-synthesizer/claude-folder-backup.zip`  
**Extracted to:** `stats/backups/meet-chavda/.claude/projects/`  
**Developer:** meet-chavda  

### Corpus summary

| Metric | Value |
|--------|------:|
| Sessions | 32 |
| User turns | 859 |
| Assistant API messages | 8,173 |
| Models | `claude-opus-4-7`, `claude-opus-4-8`, `<synthetic>` |
| Sessions with token usage | 27 / 32 |

### Top sessions by synthesizer savings potential

| Session | Turns | Real tokens | Synth est | Save % | Tools | Cache % |
|---------|------:|------------:|----------:|-------:|------:|--------:|
| **ac4ecef7** | 415 | 542,858 | 22,850 | **97.5%** | 1,722 | 99.3% |
| 4e961ee7 | 89 | 504,347 | 25,044 | 87.0% | 628 | 51.4% |
| f0b1556a | 84 | — | 1,849 | 99.2% | 620 | 0.0% |
| 64518332 | 48 | 98,645 | 8,040 | 74.2% | 9 | 96.7% |
| 9fd659d0 | 45 | 567,501 | 810,346 | 31.0% | 382 | 99.2% |

**Note:** Negative or low save % on short sessions is expected—the synthesizer overhead (ledger + window) can exceed naive history when sessions are brief. Value concentrates in **long, tool-heavy sessions**.

**Outputs:**

- `stats/meet-chavda_corpus.jsonl` (32 session summaries)
- `stats/meet-chavda_corpus.csv`
- `stats/meet-chavda_hot_ac4ecef7.json` (deep dive export)

---

## 8. Native Claude Code Caching Analysis

Tool: `analyze_claude_caching.py --cli-root <path>`

### Corpus-wide (meet-chavda, 32 sessions)

| Metric | Value |
|--------|------:|
| User turns with `cache_read > 0` | 771 / 859 (**89.8%**) |
| User turns with `cache_write > 0` | 774 / 859 (**90.1%**) |
| Turns with **no** cache signal | 84 / 859 (9.8%) |
| Assistant msgs with `cache_read > 0` | 8,107 / 8,173 (**99.2%**) |
| Assistant msgs with `cache_write > 0` | 8,163 / 8,173 (**99.9%**) |

### Interpretation

- Claude Code uses **`cache_control` breakpoints internally**—not visible in logs; only `usage` fields are observable.
- Warm turns: median **uncached tail ≈ 6 tokens**; median **cache_read ≈ 99.3%** of input.
- Volatility stack (low → high): **system → tools → history → deltas → user message**.
- Mostly **1h TTL** cache writes (`ephemeral_1h_input_tokens`).

### What this means for us

**We do not need to teach Claude Code how to cache.** Developers already get ~99% `cache_read` on warm assistant messages. Our work is **reducing the size of the cached prefix**, not improving cache hit rate.

### Claude Code `/compact` — user-triggered, late auto-fallback

Claude Code’s compaction is a **built-in slash command** (`/compact`), not a user-installable Skill (`SKILL.md`). It is **not** the same as our synthesizer’s Dreaming loop.

| Aspect | Behavior |
|--------|----------|
| **Primary mode** | **User-triggered** — developer runs `/compact` when context feels heavy or UI hints appear |
| **Secondary mode** | **Auto-compact** — fires only when the session approaches the model context ceiling (reactive, not proactive) |
| **What it does** | Summarizes conversation history, inserts a `compact_boundary` in session logs, replaces most prior turns with a continuation summary |
| **Goal** | Avoid `context exceeded` / `prompt_too_long` — **fit in the window**, not optimize cost per turn |
| **Enforcement** | **Weak by design** — history keeps growing turn-by-turn until pressure mounts |

**Evidence from meet-chavda hot session (415 turns):**

| Compaction type | Count | Implication |
|-----------------|------:|-------------|
| Claude auto-compact (`compact_boundary` in logs) | **3** | Native compact ran rarely — ~0.7% of turns |
| Synthesizer triggers (@ 10-turn threshold) | **41** | Proactive compaction would have run ~10× more often |
| Final input prefix | **541K tokens** | Native compact did **not** prevent prefix bloat |

So on long, tool-heavy sessions Claude Code **allows history to grow** (cached at ~99% read, but still huge). Developers must **choose** to `/compact`, or wait until auto-compact fires near the limit. It is **not** an always-on, turn-by-turn history architect.

**Why our synthesizer still matters:**

```
Claude /compact     →  "We're about to overflow — emergency summarize"
Synthesizer Dreaming →  "Every N turns / N tokens — merge into cached ledger"
```

| | Claude `/compact` | Synthesizer Dreaming v4 |
|--|-------------------|-------------------------|
| Trigger | Manual or late auto | Turn threshold **or** token threshold (proactive) |
| Output | Opaque session summary | Structured **Layer 2 ledger** with `cache_control` |
| Code-aware | Generic continuation summary | File latest-state, Bash collapse, Read dedup |
| Frequency on ac4ecef7 | 3× | Would be 41× (turn-based) + token spikes |

Plugin **`PreCompact` hooks** (see Claude plugin-dev docs) let extensions inject “preserve this” text **before** native compact runs—they do not replace `/compact` and are unrelated to our proxy.

---

## 9. Hot Session Deep Dive: ac4ecef7

**Project:** `cmdb-research-repository`  
**Session ID:** `ac4ecef7-10f7-4a50-89c4-dcf30b7219ce`  
**Duration:** 415 user turns, 3,410 assistant messages  

### Token usage (final turn, cumulative from CLI logs)

| Metric | Value |
|--------|------:|
| Total input | 541,343 |
| Cache read | 537,417 (**99.3%**) |
| Output | 716,416 |
| Tool calls | 1,722 |
| Unique file paths | 234 |
| Claude `/compact` (auto only; see §8.1) | 3 |
| Synthesizer compaction triggers (@ turn 10) | 41 |

### Context growth

| Estimate | Tokens |
|----------|-------:|
| Final naive (full history) | 926,162 |
| Final synthesizer-shaped | 22,850 |
| **Compression** | **97.5%** |

Sparkline pattern: naive grows monotonically (`▁…█`); synthesizer stays flat with periodic compaction spikes.

### Top growth spikes

| Turn | Δ tokens | Tools | Notes |
|------|----------|------:|-------|
| 178 | +123,713 | 40 | Largest spike — candidate for dump compaction |
| 235 | +66,586 | 20 | Heavy assistant/tool output |
| 372 | +40,266 | 3 | Large assistant block |
| 94 | +38,323 | 55 | Early heavy tool burst |

Turn 96 in caching trace showed **+511K `cache_write`** — prefix rebuild after context shift.

### Top file re-reads

| File | Reads | Turn range |
|------|------:|------------|
| `frontend/src/pages/Admin.tsx` | 21 | 219–415 |
| `backend/pipeline/agents/a4_identification.py` | 14 | 94–378 |
| `frontend/src/components/RelationshipGraph.tsx` | 10 | 94–409 |
| `backend/pipeline/orchestrator.py` | 10 | — |

### Automated recommendations (from `analyze_hot_session.py`)

1. Use **token-based compaction trigger**, not turn-count only (415 turns).
2. Compare synthesizer ledger quality vs Claude’s 3 auto-compactions (user rarely ran `/compact` manually).
3. Ledger: keep **latest state of Admin.tsx only** (21 reads).
4. **Collapse Bash output** in ledger (684 calls).
5. **Dedupe Read snippets** (280 read operations).
6. Investigate turn 178 spike for dump-style compaction.

---

## 10. Cursor Corpus (m-coder)

**Source:** `~/.cursor/projects/` (user’s m-coder project)  
**Tool:** `import_cursor_sessions.py --project m-coder --min-turns 25`

Cursor transcripts lack per-turn API `usage`—analysis uses char-based estimates. Tool calls and file touches are present in JSONL.

### Sample long sessions (≥25 turns)

| Session | Turns | Naive est | Synth est | Save % | Tools |
|---------|------:|----------:|----------:|-------:|------:|
| e64142ab | 377 | 610,909 | 4,316 | 99.3% | 3,286 |
| 511d5225 | 191 | 401,791 | 7,380 | 98.2% | 1,712 |
| fb6a3cda | 147 | 117,442 | 8,937 | 92.4% | 826 |

Earlier analysis of user’s own Cursor session (`c53ebd02` transcript in Out-of-bound-chronicles): 53 sessions, max **464 turns** in one session—same bloat patterns as Claude CLI.

**Use case:** Train code-aware compaction rules (file re-read patterns, Bash loops) without requiring live proxy access.

---

## 11. Strategic Conclusion: Where Optimization Lives

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Code already optimizes:  CACHE HIT RATE  (~99%)         │
│  Context Synthesizer optimizes:  CACHE PAYLOAD SIZE             │
│                                  + history shape                 │
│                                  + tool/file dedup               │
└─────────────────────────────────────────────────────────────────┘
```

| Scenario | Room to optimize? |
|----------|-------------------|
| Improve cache read % (99% → 100%) | **Tiny** |
| Shrink 541K input prefix on long sessions | **Large** |
| Cut `cache_write` spikes on history growth | **Real** |
| Dedupe 21× file reads into ledger state | **Real** |
| Short sessions (<10 turns) | **Small** |
| Output token cost | **Out of scope** (model generation) |

### Two optimization axes (do not conflate)

| Axis | Question | Owner today | Our role |
|------|----------|-------------|----------|
| **Cache utilization** | “Is the prefix served from cache?” | Claude Code (~99%) | None needed |
| **Cache payload** | “How big is the prefix?” | Grows with full history | **Core value** |

---

## 12. Economics Worked Example

### Hot session turn 415 — same 99% cache read, different prefix size

Anthropic prompt caching (Sonnet-class, illustrative):

| Bucket | Rate (/1M) |
|--------|------------|
| Uncached input | $3.00 |
| Cache read | $0.30 |
| Cache write | $3.75 |

**Native (537K cache_read per request on warm turns):**

```
537,000 × $0.30/M ≈ $0.161 input per warm request (cached portion only)
```

**If synthesizer shrinks prefix to ~20K (same 99% cache read):**

```
20,000 × $0.30/M ≈ $0.006 input per warm request
```

**~27× cheaper on cached input** — without changing cache hit rate.

Additionally, smaller prefix → fewer/lighter `cache_write` events when history would otherwise grow (407 write turns in ac4ecef7).

---

## 13. Telemetry & Tuning Signals

### Per-request proxy telemetry (`source: proxy`)

| Field | Use |
|-------|-----|
| `usage` / `cost` | Uncached vs cache read vs cache write + savings % |
| `context.est_layer1_tokens` … `est_prompt_tokens` | Per-layer size estimates |
| `context.client_message_count` / `ignored_messages` | IDE history bloat stripped |
| `synthesis.uncached_tail_pct` | % of input at full price — **lower is better** |
| `synthesis.client_bloat_ratio` | IDE msgs ÷ optimized payload |
| `source: compaction` | Haiku cost + `ledger_delta_chars` |

### Target signals (production `Claude.md` ~200K)

| Signal | Target |
|--------|--------|
| `cache_read_pct` | **60%+** |
| `uncached_tail_pct` (warm turns) | **<15%** |
| `client_bloat_ratio` | **5×+** |
| Compaction `ledger_delta_chars` | **Negative** (ledger shrinks or stays flat) |

`collect_stats.py` prints a **SYNTHESIZER TUNING INSIGHTS** block with p90 uncached tail, turn-bucket trends, and auto-recommendations.

---

## 14. Bugs Fixed During Analysis

### Cumulative usage inflation

**Problem:** Claude CLI logs record **cumulative** `usage` on each assistant message within a turn. The initial importer **summed** these across messages, inflating totals to billions of tokens.

**Fix:** Take **max per field per turn**, and use **final turn cumulative** for session totals (`claude_parse.py`, `import_claude_sessions.py`).

Always verify: `total_input = input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.

---

## 15. Shipped vs Planned

### Shipped

| Component | Location |
|-----------|----------|
| Four-layer index-aligned payload | `proxy_tool.py` |
| Per-session `X-Session-Id` | `resolve_session_id()` |
| Async + streaming | `AsyncAnthropic`, `_handle_streaming()` |
| Dreaming @ turn 10 | `maybe_trigger_compaction()`, `dream_compact()` |
| Bifurcated telemetry + synthesis metrics | `telemetry.py` |
| 12-turn simulator | `test_simulator.py` |
| Mode A/C/D importers | `import_*.py` |
| Hot session analyzer | `analyze_hot_session.py` |
| Native caching analyzer | `analyze_claude_caching.py` |
| Team stats rollup | `collect_stats.py` |
| Dreaming v4 + token/turn compaction | `compaction.py`, `proxy_tool.py` |

### Planned (pre-production)

| Item | Notes |
|------|-------|
| Full ~200K production `Claude.md` | Team architecture corpus; starter ~380 tokens |
| `import_claude_backup.sh` | One-command unzip + import pipeline |
| Phase 2 benchmark with production L1 | Re-run `test_simulator.py` |

---

## 16. Next Steps: Implement, Test, Deploy

Ordered workstream after this report:

### Phase 1 — Implement smart synthesis *(done)*

1. **Dreaming v4 prompt** — `compaction.py`
2. **Token-based compaction** — `COMPACTION_TOKEN_THRESHOLD`
3. **Production L1 builder** — `build_production_claude_md.py`
4. **Layer 3 cap** — `MAX_LAYER3_TURNS`

### Phase 2 — Test (corpus-first)

1. `import_claude_sessions.py` on team backups — regression on compression estimates.
2. `analyze_hot_session.py` on 100+ turn sessions — file re-reads, growth spikes.
3. `analyze_claude_caching.py` — confirm native cache read % vs synthesizer counterfactual.
4. Weekly Mode D/C exports → `collect_stats.py` corpus insights block.
5. *(Optional internal)* `test_simulator.py` with `Claude.production.md` — gateway bifurcation only.

### Phase 3 — Deploy (corpus-first, no package)

1. **Max / Pro devs:** Mode D weekly corpus export → `stats/` (no install, no proxy).
2. **Cursor devs:** Mode C same pattern.
3. **Team lead:** `collect_stats.py --logs context-synthesizer/stats/` weekly.

### Success criteria (Phase 2)

| Metric | Target | Source |
|--------|--------|--------|
| Compression est. | ≥90% on 100+ turn sessions | Mode D `extra.compression_ratio_est` |
| File re-reads | Declining in hot-session reports | `analyze_hot_session.py` |
| Native `cache_read` % | High on warm turns (baseline OK) | Mode D / `analyze_claude_caching.py` |
| Corpus regression | Stable week-over-week on same sessions | `import_claude_sessions.py` |

---

## 17. Repository Reference

### Core gateway

| File | Purpose |
|------|---------|
| `proxy_tool.py` | FastAPI gateway `:8080`, session state, compaction |
| `telemetry.py` | Cost math, `ContextSnapshot`, `SynthesisMetrics` |
| `models.py` | Model ID registry |
| `Claude.md` | Layer 1 rules (replace for production) |

### Analysis pipeline

| File | Purpose |
|------|---------|
| `import_claude_sessions.py` | Mode D — Claude Max corpus |
| `import_cursor_sessions.py` | Mode C — Cursor transcripts |
| `import_cli_logs.py` | Mode A — default Claude CLI import |
| `analyze_hot_session.py` | Single-session deep dive |
| `analyze_claude_caching.py` | Native caching behavior |
| `collect_stats.py` | Team aggregate + tuning insights |
| `claude_parse.py` / `cursor_parse.py` | Shared transcript parsers |
| `session_models.py` | `SessionAnalysis`, `TurnSnapshot` |

### Test & ops

| File | Purpose |
|------|---------|
| `test_simulator.py` | 12-turn JetBrains client simulator |
| `count_tokens.py` | Layer 1 token budget verifier |
| `build_production_claude_md.py` | Assemble Layer 1 from markdown sources |

### Data artifacts (gitignored except samples)

| Path | Contents |
|------|----------|
| `claude-folder-backup.zip` | meet-chavda backup (source) |
| `stats/backups/meet-chavda/` | Extracted `~/.claude/projects/` |
| `stats/meet-chavda_corpus.jsonl` | 32-session corpus |
| `stats/meet-chavda_hot_ac4ecef7.json` | Hot session export |

### Commands cheat sheet

```bash
# Mode A — default Claude CLI import
.venv/bin/python context-synthesizer/import_cli_logs.py --output stats/baseline.jsonl

# Mode D — Claude Max corpus
.venv/bin/python context-synthesizer/import_claude_sessions.py --developer meet-chavda --min-turns 25
.venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --largest
.venv/bin/python context-synthesizer/analyze_claude_caching.py --cli-root stats/backups/meet-chavda/.claude/projects

# Cursor corpus
.venv/bin/python context-synthesizer/import_cursor_sessions.py --project m-coder --min-turns 25

```

---

## 18. Glossary

| Term | Definition |
|------|------------|
| **Bifurcation** | Splitting input cost into uncached / cache read / cache write buckets |
| **Cache read** | Prefix served from Anthropic prompt cache ($0.30/M) |
| **Cache write** | Prefix stored into cache ($3.75/M) — cold start or bust |
| **Dreaming** | Background Haiku compaction of rolling turns into ledger |
| **`/compact`** | Claude Code built-in slash command — user-triggered summary; rare late auto-compact (§8.1) |
| **History ledger** | Layer 2 synthesized architectural state |
| **Mode A** | Default Claude CLI log import (`import_cli_logs.py`) |
| **Mode C** | Offline Cursor transcript import |
| **Mode D** | Enriched Claude Max / Pro corpus import |
| **Naive context** | Full cumulative transcript size (counterfactual without synthesizer) |
| **Uncached tail** | Tokens after last `cache_control` breakpoint (`input_tokens`) |
| **Warm turn** | Request where `cache_read_input_tokens > 0` |

---

*Report generated from engineering sessions, proxy benchmarks, and meet-chavda / m-coder corpus analysis. For questions or updates, extend this file rather than scattering findings across chat logs.*

<!-- SOURCE: /home/harshil/Out-of-bound-chronicles/context-synthesizer/SYNTHESIZER_RND_REPORT.md sha256:b3999cd507e5 -->


# BENCHMARK_ANALYSIS.md

# Benchmark Analysis — 12-Turn Simulator Run

> **Not a team workflow.** Internal gateway validation via `test_simulator.py` + `proxy_tool.py`.
> Team data collection uses offline **Modes A / C / D** — see [README.md](README.md).

**Date:** 2026-06-10  
**Session:** `simulator-benchmark`  
**Model:** `claude-sonnet-4-6`  
**Endpoint:** `http://127.0.0.1:8080/v1/messages`  
**Total wall time:** 200.31 seconds  

This document explains the simulator output line-by-line: what each number means, how it maps to proxy layers, and why savings were only **10.2%** in this run (versus the **~90%** target at production scale).

**Related docs:**

- [Context Synthesizer technical report](../context_os_technical_report.md) — architecture, shipped vs planned, §8.1 summary
- [README](README.md) — quick start
- [Anthropic Prompt Caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

**Corpus note:** Shipped starter `Claude.md` is ~380 tokens (below Sonnet 4.6's 1,024-token cache minimum). Production target is ~200K tokens — re-run after swapping the file.

---

## 1. The three-way bifurcation (Anthropic billing)

Every API response includes a `usage` object. Input cost splits into **three buckets** — this is the core bifurcation:

| Bucket | API field | Price (/1M tokens) | Meaning |
|--------|-----------|-------------------|---------|
| **Uncached input** | `input_tokens` | $3.00 | Tokens **after** the last `cache_control` breakpoint |
| **Cache read** | `cache_read_input_tokens` | $0.30 | Prefix **before** the last breakpoint, already in cache (**90% discount**) |
| **Cache write** | `cache_creation_input_tokens` | $3.75 | Prefix **before** the last breakpoint, being stored now (~25% premium) |
| **Output** | `output_tokens` | $15.00 | Generated response (not cacheable) |

### The one formula (from Anthropic)

```text
total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
```

**Spatial layout:**

- `cache_read_input_tokens` = prefix before breakpoint, **already cached** (reads)
- `cache_creation_input_tokens` = prefix before breakpoint, **being cached now** (writes)
- `input_tokens` = everything **after** your last `cache_control` breakpoint (not eligible for cache)

> **Important:** `input_tokens` is **not** your full prompt. On a warm turn with 200K cached rules, `input_tokens` might be only ~3,000 (sliding history + new question) while `cache_read_input_tokens` is ~200,500.

### Before vs after (per request)

```
BEFORE (unoptimized baseline):
  All input tokens billed at $3.00/M
  total_input = uncached + cache_read + cache_write

AFTER (with prompt caching):
  uncached  × $3.00/M
  cache_read × $0.30/M   ← savings live here
  cache_write × $3.75/M
```

### Your cumulative numbers

| Metric | Tokens | Role |
|--------|--------|------|
| Uncached input | 22,715 | Layer 3 sliding window + Layer 4 prompts + overhead |
| Cache read | 16,202 | Stable prefix hits (mostly Layer 1 + Layer 2 when warm) |
| Cache write | 15,755 | Cold starts and prefix rewrites |
| Output | 10,010 | Assistant replies (`max_tokens=1024` cap in simulator) |

| Cost | Amount |
|------|--------|
| **Baseline** (all input @ $3/M + output) | **$0.3142** |
| **Realized** (tiered pricing) | **$0.2822** |
| **Saved** | **$0.0319 (10.2%)** |
| **Cache efficiency** | **29.6%** = cache_read ÷ total_input |

---

## 2. Mapping buckets → proxy layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 1 │ messages[0] │ Claude.md (~400 tokens in THIS run)         │
│            cache_control: ephemeral                          ← BP #1    │
├─────────────────────────────────────────────────────────────────────────┤
│  Layer 2 │ messages[1] │ History Ledger (~50 tokens, static until T10)  │
│            cache_control: ephemeral                          ← BP #2    │
├─────────────────────────────────────────────────────────────────────────┤
│  Layer 3 │ messages[2..N-1] │ Rolling turns (up to 10, then cleared)   │
│            NO cache_control → always uncached                            │
├─────────────────────────────────────────────────────────────────────────┤
│  Layer 4 │ messages[N] │ Fresh user prompt each turn                    │
│            NO cache_control → always uncached                            │
└─────────────────────────────────────────────────────────────────────────┘
                                                          OUTPUT → output_tokens
```

| Layer | Content | Typical billing bucket | This run |
|-------|---------|------------------------|----------|
| **Layer 1** | `Claude.md` (pre-context) | `cache_write` → then `cache_read` | ~380 tok — **below 1,024 min** for Sonnet 4.6 |
| **Layer 2** | History ledger + fixed prefix | `cache_write` → then `cache_read` | ~55 tok; cached with L1 from Turn 4 |
| **Layer 3** | Sliding user/assistant turns | `input_tokens` (uncached) | Dominates uncached growth Turns 2–10 |
| **Layer 4** | Fresh user prompt | `input_tokens` (uncached) | Spikes on Turn 11 (massive code block) |

**Mental model:**

- **Pre-context** (Layer 1 + Layer 2) = before last breakpoint → `cache_read` / `cache_creation`
- **History** (Layer 3) + **new prompt** (Layer 4) = after last breakpoint → `input_tokens`
- **Output** = `output_tokens`

---

## 3. Worked examples with prompt sizes

### 3.1 Example payload — Turn 7 (`latency`)

What the proxy actually sent to Anthropic on Turn 7:

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": [{
        "type": "text",
        "text": "<ENTIRE Claude.md file>",
        "cache_control": { "type": "ephemeral" }
      }]
    },
    {
      "role": "user",
      "content": [{
        "type": "text",
        "text": "Current Architectural State:\nInitial State: System active and optimized.",
        "cache_control": { "type": "ephemeral" }
      }]
    },
    { "role": "user",      "content": "Initialize project context..." },
    { "role": "assistant", "content": "Based on the project context..." },
    { "role": "user",      "content": "Summarize the high-level architecture..." },
    { "role": "assistant", "content": "## High-Level Architecture..." },
    "... turns 3–6 (user + assistant pairs) ...",
    {
      "role": "user",
      "content": "Suggest ways to keep proxy latency low while preserving cache hit rates."
    }
  ]
}
```

---

### 3.2 Example A — Production target (200K `Claude.md`, warm Turn 8)

**Assumed block sizes** (use `count_tokens.py` on your real file for exact Layer 1):

| Block | Content | Est. tokens | Billing bucket (warm turn) |
|-------|---------|-------------|----------------------------|
| **Layer 1** | Full `Claude.md` rules | **200,000** | `cache_read` @ $0.30/M |
| **Layer 2** | History ledger | **500** | `cache_read` @ $0.30/M |
| **Layer 3** | 6 recent user+assistant pairs | **3,000** | `input_tokens` @ $3.00/M |
| **Layer 4** | New question | **40** | `input_tokens` @ $3.00/M |
| **Output** | Assistant reply | **800** | `output_tokens` @ $15.00/M |

**API `usage` on a warm turn:**

```json
{
  "cache_read_input_tokens": 200500,
  "cache_creation_input_tokens": 0,
  "input_tokens": 3040,
  "output_tokens": 800
}
```

Check: `200,500 + 0 + 3,040 = 203,540` total input ✓

**Cost bifurcation (Sonnet 4.6):**

| Bucket | Tokens | Rate | Cost |
|--------|--------|------|------|
| Cache read (L1+L2) | 200,500 | $0.30/M | **$0.0602** |
| Uncached (L3+L4) | 3,040 | $3.00/M | **$0.0091** |
| Output | 800 | $15.00/M | **$0.0120** |
| **Actual total** | | | **$0.0813** |

**Without caching (baseline — all input @ $3/M):**

| | Tokens | Cost |
|--|--------|------|
| All input | 203,540 | **$0.6106** |
| Output | 800 | $0.0120 |
| **Baseline total** | | **$0.6226** |

**Saved on this one turn: ~$0.54 (87%)** — almost entirely from Layer 1.

This mirrors Anthropic's doc example: *100,000 cache read + 50 user tokens → `cache_read=100,000`, `input_tokens=50`*. Your design scales that to **200K on Layer 1**.

---

### 3.3 Example B — Your real benchmark, Turn 7 (`latency`)

**Reported `usage`:**

| API field | Value |
|-----------|-------|
| `cache_read_input_tokens` | **2,541** |
| `cache_creation_input_tokens` | **1,492** |
| `input_tokens` | **1,074** |
| `output_tokens` | **1,024** |

**Estimated block sizes** (starter `Claude.md`, not production):

| Block | Est. tokens | Where in `usage` |
|-------|-------------|------------------|
| **Layer 1** — `Claude.md` | **~380** | Part of `cache_read` + `cache_creation` (combined with L2) |
| **Layer 2** — ledger + `"Current Architectural State:\n"` | **~55** | Part of `cache_read` + `cache_creation` |
| **Layer 3** — turns 1–6 (12 messages) | **~1,020** | **`input_tokens`** |
| **Layer 4** — `"Suggest ways to keep proxy latency low..."` | **~15** | **`input_tokens`** |
| **Output** — assistant answer | **1,024** | **`output_tokens`** (hit `max_tokens` cap) |

**Sanity checks:**

- L3 + L4: `~1,020 + ~15 ≈ 1,035` ≈ reported **`input_tokens: 1,074`** ✓ (gap = message formatting overhead)
- Total input: `2,541 + 1,492 + 1,074 = **5,107**` tokens processed

**Why `cache_read` is 2,541 (not ~435):**

Starter `Claude.md` is **~380 tokens** — below Sonnet 4.6's **1,024-token minimum** per cache block. Layer 1 alone cannot cache.

| Phase | Observation |
|-------|-------------|
| Turns 1–3 | `cache_read=0`, `cache_write=0` — nothing cacheable yet |
| Turn 4 | `cache_write=2,519` — first large enough prefix stored |
| Turn 7 | `cache_read=2,541` + `cache_write=1,492` — partial hit + partial rewrite on prefix region |

The prefix region exceeds L1+L2 alone because Anthropic accounts for message structure, breakpoints, and matching prior request prefixes across the session.

**Turn 7 cost (Sonnet 4.6):**

| Bucket | Tokens | Rate | Cost |
|--------|--------|------|------|
| Cache read | 2,541 | $0.30/M | $0.00076 |
| Cache write | 1,492 | $3.75/M | $0.00560 |
| Uncached (L3+L4) | 1,074 | $3.00/M | $0.00322 |
| Output | 1,024 | $15.00/M | $0.01536 |
| **Actual** | | | **$0.0249** |

**Baseline** (all 5,107 input @ $3/M): input $0.0153 + output $0.0154 = **$0.0307**  
**Saved:** ~$0.006 (~19%) on this turn — modest because cached prefix is ~2.5K tokens, not 200K.

---

### 3.4 Side-by-side: Turn 1 vs warm turn

#### Production (200K `Claude.md`)

| | Turn 1 (cold) | Turn 8 (warm) |
|--|---------------|---------------|
| **L1 Claude.md** | 200,000 → `cache_creation` | 200,000 → `cache_read` |
| **L2 Ledger** | 500 → `cache_creation` | 500 → `cache_read` |
| **L3 History** | 0 | ~3,500 → `input_tokens` |
| **L4 New prompt** | ~40 → `input_tokens` | ~40 → `input_tokens` |
| **Output** | ~800 | ~800 |
| **Dominant cost** | cache **write** (~$0.75+) | cache **read** (~$0.06) |

#### This benchmark (starter file)

| | Turn 1 | Turn 7 |
|--|--------|--------|
| **L1** | ~380 (no cache) | ~380 |
| **L2** | ~55 | ~55 |
| **L3** | 0 | ~1,020 |
| **L4** | ~30 | ~15 |
| **Output** | 327 | 1,024 |
| **`cache_read`** | 0 | 2,541 |
| **`cache_write`** | 0 | 1,492 |
| **`input_tokens`** | 452 | 1,074 |

---

### 3.5 Measuring exact block sizes

```bash
# Layer 1 only (exact, with cache_control block shape)
.venv/bin/python context-synthesizer/count_tokens.py

# Layer 1 + Layer 2: count via API with both message blocks
# (future: count_all_layers() helper in proxy_tool.py)
```

**Deriving Layer 3 + Layer 4 on any warm turn:**

```text
input_tokens ≈ Layer 3 tokens + Layer 4 tokens
```

From Turn 7: **L3 ≈ 1,074 − 15 ≈ 1,059 tokens**.

---

## 4. Turn-by-turn narrative

### Phase A — Cold cache (Turns 1–3)

| Turn | Label | Uncached | Cache Rd | Cache Wr | Output | What happened |
|------|-------|----------|----------|----------|--------|---------------|
| 1 | bootstrap | 452 | 0 | 0 | 327 | First request. No cache activity. L1+L2 too small or below cache threshold. |
| 2 | architecture | 803 | 0 | 0 | 672 | Sliding window +1 exchange. All fresh input. |
| 3 | cache-design | 1,495 | 0 | 0 | 1,024 | Window growing; output hit `max_tokens=1024` cap. |

**Insight:** Zero `cache_read` and zero `cache_write` means **no prompt cache was engaged yet**. Starter `Claude.md` is ~400 tokens — under Anthropic's **1,024-token minimum** per `cache_control` block for Sonnet 4.6.

---

### Phase B — First cache write (Turn 4)

| Turn | Label | Uncached | Cache Rd | Cache Wr | Output |
|------|-------|----------|----------|----------|--------|
| 4 | jetbrains-format | **25** | 0 | **2,519** | 447 |

**Insight:** First major `cache_creation` (2,519 tokens). Almost the entire prefix was written to cache; only **25 uncached tokens** (Layer 4). Investment turn — pay $3.75/M now to enable $0.30/M reads later.

---

### Phase C — Warm cache with growing window (Turns 5–10)

| Turn | Label | Uncached | Cache Rd | Cache Wr | Output | Δ Cache Rd |
|------|-------|----------|----------|----------|--------|------------|
| 5 | index-layout | 491 | 0 | 2,519 | 1,024 | — (rewrite) |
| 6 | telemetry | 1,073 | 1,492 | 1,496 | 1,024 | +1,492 |
| 7 | latency | 1,074 | 2,541 | 1,492 | 1,024 | +1,049 |
| 8 | streaming | 1,068 | 3,007 | 2,078 | 1,024 | +466 |
| 9 | error-handling | 1,065 | 4,058 | 2,073 | 1,024 | +1,051 |
| 10 | threshold | 1,066 | 5,104 | 2,073 | 1,024 | +1,046 |

**Patterns:**

1. **Uncached ~1,065–1,074** (Turns 6–10) — stable per-turn tax: Layer 4 + growing Layer 3.
2. **Cache read climbing ~1,000/turn** — expanding identical prefix across session.
3. **Simultaneous cache_write ~1,500–2,000** — partial prefix rewrites.
4. **Turn 10** hits `MAX_TURNS_THRESHOLD` → compaction triggered.

---

### Phase D — Compaction shock + massive prompt (Turns 11–12)

| Turn | Label | Uncached | Cache Rd | Cache Wr | Output | Event |
|------|-------|----------|----------|----------|--------|-------|
| 11 | massive-code-review | **6,745** | **0** | 0 | 1,024 | 200-line Java block in Layer 4; cache cold |
| 12 | wrap-up | **7,358** | 0 | 1,505 | 372 | Ledger rewritten; cache rebuilding |

**Insight:**

- **Turn 11:** `cache_read=0` — compaction changed Layer 2 + huge Layer 4 payload.
- **Turn 12:** `cache_write=1,505` — paying to warm cache after ledger mutation.

---

## 5. Visual timeline

```
Turn:  1    2    3    4    5    6    7    8    9   10   11   12
       │    │    │    │    │    │    │    │    │    │    │    │
Cache  ░░░░ ░░░░ ░░░░ ▓▓▓▓ ▓▓▓▓ ████ ████ ████ ████ ████ ░░░░ ▓▓▓▓
Read   0    0    0    0    0   1.5k 2.5k 3.0k 4.1k 5.1k  0   0

Cache  0    0    0   2.5k 2.5k 1.5k 1.5k 2.1k 2.1k 2.1k  0   1.5k
Write

Uncached grows ───────────────────────────────► spike ──► spike
              (sliding window)                  (T11)    (T12)
```

---

## 6. Why only 10.2% savings (not 90%)

| Factor | This run | Production target |
|--------|----------|-------------------|
| Layer 1 size | ~400 tokens | ~200,000 tokens |
| Cache-eligible prefix | ~2,500 tokens | ~200,500 tokens |
| Cost of prefix per warm turn @ full price | ~$0.0075 | ~$0.60 |
| Cost of prefix per warm turn @ cache read | ~$0.00075 | ~$0.06 |
| **Per-turn savings on Layer 1 alone** | **~$0.007** | **~$0.54** |

**Root cause:** Starter `Claude.md` is a placeholder. The 90% discount applies to **cached prefix tokens**. With ~2.5K cacheable vs ~23K uncached, uncached dominates spend.

### Projected production math (illustrative)

```
Baseline:  12 × (200,500 × $3/M)  ≈ $7.22 input only
Realized:  1 × (200,500 × $3.75/M)  [write]
         + 10 × (200,500 × $0.30/M) [read]
         + 12 × (1,000 × $3/M)       [uncached L3+L4]
         ≈ $0.75 + $0.60 + $0.04 ≈ $1.39 input
Savings:   ~80%+ on input cost
```

---

## 7. Cost bifurcation ledger (cumulative)

| Component | Tokens | @ Rate | Cost |
|-----------|--------|--------|------|
| Uncached input | 22,715 | $3.00/M | $0.0681 |
| Cache read | 16,202 | $0.30/M | $0.0049 |
| Cache write | 15,755 | $3.75/M | $0.0591 |
| Output | 10,010 | $15.00/M | $0.1502 |
| **Realized total** | | | **$0.2822** |

**If all input were uncached (before):**

| Component | Tokens | @ Rate | Cost |
|-----------|--------|--------|------|
| All input | 54,672 | $3.00/M | $0.1640 |
| Output | 10,010 | $15.00/M | $0.1502 |
| **Baseline total** | | | **$0.3142** |

**Where the $0.0319 saved came from:**

- Cache reads (16,202 tok @ 90% off vs $3/M) → **~$0.044 saved**
- Cache writes (15,755 tok @ 25% premium) → **~$0.012 extra cost**
- Net ≈ **$0.032** ✓

---

## 8. Action items to reach target savings

1. **Replace `Claude.md`** with your full ~200K-token rules corpus.
2. **Verify:** `.venv/bin/python context-synthesizer/count_tokens.py` → confirm ≥ 1,024 tokens (ideally ~200K).
3. **Re-run:** `.venv/bin/python context-synthesizer/test_simulator.py`
4. **Expect Turn 1:** large `cache_creation` (~200K).
5. **Expect Turns 2–9:** large `cache_read` (~200K), small `uncached` (~1K).
6. **Expect Turn 10+:** one-time `cache_write` on ledger compaction; Layer 1 should **stay** `cache_read`.

---

## 9. Quick reference — reading the simulator table

| Column | Meaning |
|--------|---------|
| **Latency** | Round-trip through proxy → Anthropic → proxy |
| **Uncached** | Layer 3 + Layer 4 + any cache miss (`input_tokens`) |
| **Cache Rd** | Prefix served from cache at 90% discount (`cache_read_input_tokens`) |
| **Cache Wr** | Prefix stored into cache (`cache_creation_input_tokens`) |
| **Output** | Assistant response size (`output_tokens`) |

| Simulator summary field | Meaning |
|-------------------------|---------|
| **Baseline Total Cost** | "Before" — no caching benefit |
| **Realized Cost** | "After" — actual tiered billing |
| **Savings Rate** | `(baseline − realized) / baseline` |
| **Cache Efficiency Rate** | `cache_read / total_input` — how much input hit cache |

---

## 10. Conclusion

The proxy's index-aligned layout behaved correctly:

- Cache engaged from Turn 4 onward.
- Cache reads scaled during Turns 6–10.
- Turn 10 compaction and Turn 11's massive prompt caused predictable cache invalidation.
- Overall savings were modest (**10.2%**) because **the cached prefix was ~2.5K tokens, not 200K**.

**The bifurcation is working. The corpus is not yet production-sized.**

Next step: load the real `Claude.md`, re-run the simulator, and compare Section 3.2 warm-turn patterns against `cache_read ≈ 200,000`.

See also: [Context Synthesizer technical report](../context_os_technical_report.md) for full architecture and shipped vs. planned features.

<!-- SOURCE: /home/harshil/Out-of-bound-chronicles/context-synthesizer/BENCHMARK_ANALYSIS.md sha256:223772ee6713 -->


# Usage.md

# Context Synthesizer — Developer Setup Guide

## Modes at a glance

All modes are **offline** — import session logs from disk. No API key, no proxy, no install.

| Mode | Who | Tool | Data path |
|------|-----|------|-----------|
| **A** | Default — Claude Code | `import_cli_logs.py` | `~/.claude/projects/<project>/<session>.jsonl` |
| **C** | Cursor IDE | `import_cursor_sessions.py` | `~/.cursor/projects/.../agent-transcripts/` |
| **D** | Claude Max / Pro | `import_claude_sessions.py` | `~/.claude/projects/<project>/<session>.jsonl` |

| | Mode A | Mode D |
|--|--------|--------|
| Import depth | Per-assistant-turn `usage` | Full session analysis + synthesizer counterfactual |
| Best for | Quick weekly token snapshot | Synthesizer R&D, hot sessions, team corpus |

Full comparison: [README § Data collection modes](README.md#data-collection-modes).

---

## Mode A — Default (Claude Code)

Claude Code stores every session locally. Mode A imports assistant turns with real token `usage`.

```bash
cd ~/Out-of-bound-chronicles
export TELEMETRY_DEVELOPER_ID="your-github-handle"

.venv/bin/python context-synthesizer/import_cli_logs.py \
  --output context-synthesizer/stats/$(whoami)_cli.jsonl

# Optional: only recent sessions
.venv/bin/python context-synthesizer/import_cli_logs.py --since 2026-06-01
```

Send `stats/*_cli.jsonl` to your team lead. See [CLI_STATS_GUIDE.md](CLI_STATS_GUIDE.md) for field details.

---

## Mode D — Claude Max / Pro (recommended for synthesizer R&D)

Same log paths as Mode A, but richer analysis: turn growth, file re-reads, compression estimates, cache read %.

```bash
.venv/bin/python context-synthesizer/import_claude_sessions.py \
  --developer your-github-handle \
  --min-turns 25 \
  --export stats/$(whoami)_claude.csv
```

### Deep-dive one long session

```bash
.venv/bin/python context-synthesizer/analyze_hot_session.py \
  --source claude --largest --export stats/hot_session.json
```

### Filter by project

```bash
.venv/bin/python context-synthesizer/import_claude_sessions.py --project my-repo-name
.venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --project my-repo --largest
```

---

## Mode C — Cursor IDE

```bash
.venv/bin/python context-synthesizer/import_cursor_sessions.py --project m-coder --min-turns 25
.venv/bin/python context-synthesizer/analyze_hot_session.py --source cursor --project m-coder --largest
```

Cursor logs lack per-turn API `usage` — analysis uses char-based estimates. Claude Mode D is richer for token bifurcation.

---

## Team lead: aggregate corpus

Collect corpus files from developers (default output paths):

| Mode | Default file | JSONL `source` tag |
|------|--------------|-------------------|
| A | `stats/telemetry.jsonl` (or custom `--output`) | `cli_import` |
| D | `stats/claude_corpus.jsonl` | `claude_corpus` |
| C | `stats/cursor_corpus.jsonl` | `cursor_import` |

```bash

.venv/bin/python context-synthesizer/collect_stats.py \
  --logs context-synthesizer/stats/ \
  --group-by developer_id \
  --export stats/team_report.csv
```

Use `--source claude_corpus` to filter Mode D only. For compression deep-dives, prefer `analyze_hot_session.py`.

---

## What each mode provides

| Mode | API key? | Token bifurcation | Session shape | Synthesizer counterfactual |
|------|----------|-------------------|---------------|--------------------------|
| **A** | No | Yes (assistant turns) | Limited | No |
| **D** | No | Yes (full session) | Yes | Yes |
| **C** | No | Estimates only | Yes | Yes (char-based) |

---

## Building the smart synthesizer from corpus data

1. **Collect** long sessions (`--min-turns 25`) — Mode D or C
2. **Analyze** hot sessions — file re-reads, growth spikes, tool loops
3. **Tune** compaction prompts and thresholds in `compaction.py` / `proxy_tool.py`
4. **Validate** compression estimates against new weekly exports

Target signals:
- Files read 10+ times → ledger should hold latest snippet only
- Naive context >> synth estimate → synthesizer has high value
- Low `cache_read` % in Claude logs → production `Claude.md` sizing (gateway target)

---

## Troubleshooting

### `~/.claude/projects` not found

Run Claude Code in at least one project directory first.

### No token usage in import

Older CLI versions may omit `usage` on some lines — upgrade Claude Code.

---

## Further reading

| Doc | Contents |
|-----|----------|
| [CLI_STATS_GUIDE.md](CLI_STATS_GUIDE.md) | Mode A import details |
| [SYNTHESIZER_RND_REPORT.md](SYNTHESIZER_RND_REPORT.md) | Corpus findings + roadmap |
| [README.md](README.md) | Architecture overview |

<!-- SOURCE: /home/harshil/Out-of-bound-chronicles/context-synthesizer/Usage.md sha256:af499fb736e5 -->


# context_os_technical_report.md

# Context Synthesizer (Context-OS)
## A Field Engineer's Guide to LLM Context Economy

---

> **What this document is:** Engineering record for the **Context Synthesizer** proxy — design rationale (LLM physics, caching economics, OS memory analogy) plus what is **shipped** in `context-synthesizer/` vs **planned** next.
>
> **Companion docs:** [`README.md`](context-synthesizer/README.md) · [`Usage.md`](context-synthesizer/Usage.md) · [`SYNTHESIZER_RND_REPORT.md`](context-synthesizer/SYNTHESIZER_RND_REPORT.md) · [`CLI_STATS_GUIDE.md`](context-synthesizer/CLI_STATS_GUIDE.md)

---

## Shipped vs. Planned

| Feature | Status | Location / notes |
|---------|--------|------------------|
| Four-layer index-aligned payload | **Shipped** | `proxy_tool.py` — `build_optimized_messages()` |
| Ignore IDE cumulative history; use last user turn only | **Shipped** | `normalize_content(incoming_messages[-1])` |
| Per-session state via `X-Session-Id` header | **Shipped** | `resolve_session_id()` — not in message body |
| `cache_control` on Layer 1 + Layer 2 | **Shipped** | `build_layer1_message()`, `build_layer2_message()` |
| Async Anthropic client | **Shipped** | `AsyncAnthropic` |
| Streaming (`stream: true` → SSE) | **Shipped** | `_handle_streaming()` |
| Bifurcated telemetry (terminal + JSONL) | **Shipped** | `telemetry.py` — `record_telemetry()` |
| Dreaming v4 compaction | **Shipped** | `compaction.py` + `dream_compact()` in `proxy_tool.py` |
| Turn + token compaction triggers | **Shipped** | `MAX_TURNS_THRESHOLD`, `COMPACTION_TOKEN_THRESHOLD`, `MAX_LAYER3_TURNS` |
| Haiku compaction model | **Shipped** | `claude-haiku-4-5-20251001` via `COMPACTION_MODEL` |
| Mode A/C/D offline importers | **Shipped** | `import_cli_logs.py`, `import_cursor_sessions.py`, `import_claude_sessions.py` |
| Hot session + caching analyzers | **Shipped** | `analyze_hot_session.py`, `analyze_claude_caching.py` |
| Production L1 builder | **Shipped** | `build_production_claude_md.py` |
| 12-turn JetBrains simulator | **Shipped** | `test_simulator.py` (internal gateway validation) |
| Layer 1 token budget verifier | **Shipped** | `count_tokens.py` |
| Team stats aggregator + CSV export | **Shipped** | `collect_stats.py` |
| Model registry | **Shipped** | `models.py` |
| Full ~200K production `Claude.md` | **Planned** | Team architecture corpus; starter ~380 tokens |
| `import_claude_backup.sh` | **Planned** | One-shot unzip + import |
| State Override validation | **Partial** | Rules in Dreaming v4; stricter post-check planned |
| Asymmetric tiered routing (§7) | **Planned** | Not in codebase |
| Per-layer token counts in telemetry | **Planned** | Char estimates in `ContextSnapshot` today |

---

## Table of Contents

1. [The Problem: Why Long Sessions Bleed Money](#1-the-problem)
2. [The Physics: Why You Can't Just "Skip" Old Context](#2-the-physics)
3. [The Economics: How Prompt Caching Changes Everything](#3-the-economics)
4. [The OS Analogy: Borrowing from Operating System Design](#4-the-os-analogy)
5. [Architecture: The Four-Layer Context Stack](#5-architecture)
6. [The Dreaming Loop: Asynchronous State Synthesis](#6-the-dreaming-loop)
7. [Future: Asymmetric Tiered Routing](#7-future-asymmetric-tiered-routing)
8. [Telemetry: Measuring What You Save](#8-telemetry)
9. [Implementation: Repository Layout](#9-implementation-repository-layout)
10. [Deployment: JetBrains Team Rollout](#10-deployment-jetbrains-team-rollout)
11. [Ecosystem Comparison](#11-ecosystem-comparison)
12. [Comprehension Checkpoints](#12-comprehension-checkpoints)

---

## 1. The Problem

### The Context Tax

Imagine a developer working on a large Java microservices product. They've built a 200,000-token `Claude.md` file — a detailed blueprint of their architecture, coding conventions, API contracts, and domain rules. Every time they ask the AI assistant a question, this file needs to accompany the request so the AI understands the full context of the system.

By turn 15 of a debugging session, the payload sent to the API *without optimization* looks like this:

```
Component                    | Token Count
-----------------------------|-------------
Claude.md (architecture)     | 200,000
Chat history (15 turns)      | 150,000
Current prompt               |   5,000
-----------------------------|-------------
TOTAL INPUT                  | 355,000
Expected output              |   4,000
```

**The uncomfortable truth:** To get a 4,000-token answer, you are paying for 355,000 tokens of input — every single turn. And on turn 16, you pay for 359,000. This is the **Context Tax**: the cost of re-sending the same background knowledge because the model has no persistent memory of its own.

### Why This Matters Financially

At Claude Sonnet 4.6's standard input rate of $3.00 per 1M tokens:

```
50 turns × ~355,000 avg input tokens = 17,750,000 tokens
17,750,000 ÷ 1,000,000 × $3.00 = $53.25 per session (naive)
```

The **target** for Context Synthesizer is ~80–90% input-cost reduction once a production-sized `Claude.md` is cached. Measured savings on the starter corpus were **10.2%** — see [§8.1](#81-empirical-benchmark-2026-06-10).

---

## 2. The Physics

### Why Can't the Model Just "Remember" Previous Turns?

**Large Language Models are mathematically stateless.** Every API call is an isolated computation. The model cannot remember prior turns unless you re-send them.

### Autoregressive Decoding

Each output token requires attention over the full prior sequence:

```
[Claude.md (200K)] + [History (150K)] + [New Prompt (5K)]
                              │
                    Dense Attention Matrix
                              │
                    One Token Predicted (× N output tokens)
```

Dropping static rules or history makes the model blind to architecture and prior decisions.

### The KV Cache: Efficient, but Not Free

Inference engines use a **KV cache** in GPU VRAM. Cloud APIs are multi-tenant — between your requests the GPU serves other users. **Prompt caching** (Anthropic's prefix cache) lets the API reuse pre-computed prefix state when the byte-identical prefix returns within the cache TTL (~5 minutes for `ephemeral`).

---

## 3. The Economics

### Prompt Caching: The 90% Discount

Requirements for a cache breakpoint ([Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)):

1. Content at a defined position in the prompt with `cache_control: {"type": "ephemeral"}`
2. **Byte-identical** on subsequent requests (for that breakpoint's prefix)
3. Meets the **minimum cacheable length** for your model

**Sonnet 4.6 pricing (default chat model):**

| Token Type | Rate (/1M) | Notes |
|------------|------------|-------|
| Uncached input | $3.00 | `input_tokens` — tail after last breakpoint |
| Cache read | $0.30 | **90% off** base input |
| Cache write (5m) | $3.75 | 1.25× base; first-time store |
| Output | $15.00 | Not cacheable |

Other models use different base rates (e.g. Claude Fable 5: $10 / $1 / $12.50 per 1M). See `context-synthesizer/models.py` and set `ANTHROPIC_MODEL` consistently in proxy and `count_tokens.py`.

### Minimum cacheable length

For **Claude Sonnet 4.6** on the Claude API: **1,024 tokens** per cache block. Shorter blocks are processed without caching — no error returned. Verify via `cache_read_input_tokens` and `cache_creation_input_tokens` in `usage`.

The shipped starter `Claude.md` (~380 tokens) is below this threshold, which explains zero cache activity on Turns 1–3 of our benchmark.

### The Cache-Busting Vulnerability

Prefix matching is strict from index 0:

```
❌ INVALID — CACHE BUSTED
  messages[0]: "Session: user-abc-2026-06-10T09:52:11"  ← Dynamic UUID in body
  messages[1]: Claude.md block                           ← Never matches

✅ VALID — CACHE LOCKED (our proxy)
  HTTP header: X-Session-Id: user-abc                      ← Session outside payload
  messages[0]: Claude.md + cache_control                 ← Static from index 0
  messages[1]: History ledger + cache_control            ← Breakpoint 2
  messages[2..]: sliding turns + new prompt              ← Uncached tail
```

**Never** put timestamps, UUIDs, or session counters inside cached message blocks. The proxy scopes sessions via **`X-Session-Id`** (also `session-id`, `x-jetbrains-session-id`).

### Multiple cache breakpoints

Up to **4 breakpoints** per request. Context Synthesizer uses **two**:

```json
[
  { "text": "Claude.md",           "cache_control": {"type": "ephemeral"} },
  { "text": "History Ledger",      "cache_control": {"type": "ephemeral"} },
  { "text": "Rolling raw turns" },
  { "text": "New user prompt" }
]
```

Everything **after** the last breakpoint appears in `input_tokens` only. Target production: ~200K + ~500 cached, ~3–8K uncached tail per warm turn.

### The billing formula

```text
total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
```

- `cache_read_input_tokens` — prefix before last breakpoint, read from cache
- `cache_creation_input_tokens` — prefix before last breakpoint, written now
- `input_tokens` — **only** content after the last breakpoint (Layer 3 + Layer 4)

---

## 4. The OS Analogy

### Lost in the Middle

Raw transcripts growing to 150K+ tokens increase cost (uncached tail) and hurt retrieval — attention is strongest at sequence start and end.

### Memory hierarchy mapping

```
Layer 3 (rolling raw turns)     ← RAM — hot working set (uncached)
Layer 1 (Claude.md)             ← Disk page cache — KV-cached prefix
Layer 2 (synthesized ledger)    ← Swap-consolidated long-term state (KV-cached)
Post-compaction archive         ← Compressed into Layer 2 by dreaming
```

**Shipped behavior:** Layer 3 accumulates **all** user/assistant pairs since last compaction (up to **10 turns**), then clears on dreaming — not a fixed 2–3 turn cap.

### Limits of the analogy

Transformers have non-local token dependencies. Eviction is **semantic consolidation** (ledger synthesis), not arbitrary page deletion.

---

## 5. Architecture

### The Four-Layer Context Stack

The proxy rebuilds every outbound request from owned state. **JetBrains' full `messages` array is discarded** except the latest user turn (Layer 4).

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Static Architecture Blueprint                    │
│  Claude.md                                                  │
│  Target: ~200,000 tokens  |  Shipped starter: ~380 tokens   │
│  cache_control: { type: "ephemeral" }                       │
│  → Target: cache_read @ $0.30/1M after warm-up              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — Synthesized History Ledger                       │
│  Prefix: "Current Architectural State:\n" + ledger body     │
│  Target: ~500–2,000 tokens  |  Shipped: ~50 tokens initial  │
│  cache_control: { type: "ephemeral" }                       │
│  → Updated by background dreaming; invalidates L2 cache once  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — Rolling Raw Chat Window                          │
│  All user/assistant pairs since last compaction             │
│  Shipped: up to 10 exchanges, then cleared                  │
│  → No cache_control → always in input_tokens                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4 — Active User Prompt                               │
│  Latest turn from IDE (string or block array normalized)    │
│  → No cache_control → always in input_tokens                  │
└─────────────────────────────────────────────────────────────┘
```

**Invariants enforced in code:**

- No dynamic values in Layer 1 or Layer 2 bodies
- Session isolation via HTTP headers, not message content
- Layer 1 loaded once at startup from `CLAUDE_MD_PATH` (byte-stable across requests)

---

## 6. The Dreaming Loop

### Purpose

Prevent Layer 3 from growing without bound. Merge raw turns into Layer 2 asynchronously.

### Shipped trigger

```text
turn_counter >= MAX_TURNS_THRESHOLD   (default: 10, env-configurable)
```

On trigger: snapshot `rolling_recent_turns` → clear window → reset counter → `asyncio.create_task(dream_compact(...))`. The developer's next request is not blocked.

### Token trigger (shipped)

```text
turn_counter >= MAX_TURNS_THRESHOLD
  OR  est_history_tokens >= COMPACTION_TOKEN_THRESHOLD   (default: 100,000; 0 = off)
```

`MAX_LAYER3_TURNS` trims the rolling window even if compaction is delayed.

### Shipped synthesis pipeline

1. **Snapshot** — copy `rolling_recent_turns` and current ledger
2. **Async handoff** — clear Layer 3 immediately
3. **Background call** — `claude-haiku-4-5-20251001`, `dream_compact()` in `proxy_tool.py`
4. **Flush** — overwrite `session.history_ledger` under per-session lock

**Shipped compaction prompt** (summary): merge turns into ledger; preserve decisions, paths, constraints; drop boilerplate; output ledger body only.

### State Override semantics (partially shipped)

When a fact changes (e.g. PostgreSQL → MongoDB), the ledger should record **current truth only**:

```
❌  - Database: was PostgreSQL, now MongoDB
✅  - Database layer: MongoDB (document store) — relational schema deprecated
```

`dream_compact()` includes State Override instructions and a ~2,000-token cap. Stricter post-synthesis validation is planned.

---

## 7. Future: Asymmetric Tiered Routing

> **Status: Planned — not implemented.**

For prompts with no project dependency (*"Java regex for email validation"*), loading 200K+ cached context is wasteful.

```
Incoming prompt → needs project context? ──NO──► Tier 1: cheap model, no Claude.md
                              │
                             YES
                              ▼
                    Tier 2: full four-layer stack
```

Heuristic: keyword / embedding router against known modules and file paths. No code in `proxy_tool.py` today — all traffic uses the full stack.

---

## 8. Telemetry

### API `usage` fields

```json
{
  "usage": {
    "input_tokens": 3040,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 200500,
    "output_tokens": 800
  }
}
```

| Field | Meaning |
|-------|---------|
| `input_tokens` | Uncached tail **after last breakpoint** (Layer 3 + Layer 4) |
| `cache_read_input_tokens` | Cached prefix read at 90% discount |
| `cache_creation_input_tokens` | Cached prefix written (1.25× surcharge) |
| `output_tokens` | Generated response |

### Bifurcated cost model (shipped — `run_bifurcated_telemetry`)

```python
def compute_costs(usage):
    uncached   = usage.input_tokens
    cache_read = usage.cache_read_input_tokens or 0
    cache_write= usage.cache_creation_input_tokens or 0
    output     = usage.output_tokens

    actual = (
        uncached    * 3.00 +
        cache_read  * 0.30 +
        cache_write * 3.75 +
        output      * 15.00
    ) / 1_000_000

    baseline = (
        (uncached + cache_read + cache_write) * 3.00 +
        output * 15.00
    ) / 1_000_000

    return actual, baseline, baseline - actual
```

Printed per request in the proxy terminal; appended to `stats/*.jsonl`; team rollup via `collect_stats.py`.

### 8.2 Collecting stats from Claude CLI developers

See [`context-synthesizer/CLI_STATS_GUIDE.md`](context-synthesizer/CLI_STATS_GUIDE.md).

**Two modes:**

1. **Baseline** — `import_cli_logs.py` reads `~/.claude/projects/**/*.jsonl` (native CLI `usage` per assistant turn).
2. **Synthesizer** — developers set `ANTHROPIC_BASE_URL=http://127.0.0.1:8080`; proxy logs bifurcated events with `TELEMETRY_DEVELOPER_ID`.

Compare baseline vs synthesizer `savings_pct` and `cache_efficiency_pct` to tune Layer 1 size, compaction threshold, and ledger synthesis.

### 8.1 Empirical benchmark (2026-06-10)

12-turn run via `test_simulator.py` against starter `Claude.md`. Full analysis: [`context-synthesizer/BENCHMARK_ANALYSIS.md`](context-synthesizer/BENCHMARK_ANALYSIS.md).

| Metric | Measured | Production target (200K L1) |
|--------|----------|------------------------------|
| Cumulative savings | **10.2%** | **80–90%** input cost |
| Cache efficiency | **29.6%** | **70–90%+** after turn 2 |
| Layer 1 size | ~380 tokens | ~200,000 tokens |
| Turn 7 `input_tokens` | 1,074 (L3+L4) | ~3,000 |
| Turn 7 `cache_read` | 2,541 | ~200,500 |

**Conclusion:** Architecture behaved correctly; savings were modest because the cached prefix was ~2.5K tokens, not 200K. Replace `Claude.md`, re-run `count_tokens.py`, then `test_simulator.py`.

---

## 9. Implementation: Repository Layout

```
context-synthesizer/
├── proxy_tool.py          # FastAPI gateway (main entry point)
├── telemetry.py           # Bifurcated cost math + JSONL events
├── import_cli_logs.py     # Import ~/.claude/projects usage (baseline)
├── collect_stats.py       # Team aggregate report + CSV export
├── test_simulator.py      # 12-turn JetBrains client + cumulative benchmark
├── count_tokens.py        # Layer 1 token budget (--list-models)
├── models.py              # Model IDs and defaults (Sonnet 4.6, Haiku 4.5)
├── Claude.md              # Layer 1 source (replace for production)
├── stats/                 # Telemetry JSONL (gitignored)
├── CLI_STATS_GUIDE.md     # Developer stats collection workflow
├── BENCHMARK_ANALYSIS.md  # Measured run breakdown
└── README.md              # Quick start
```

### Key functions (`proxy_tool.py`)

| Function | Role |
|----------|------|
| `load_claude_md()` | Load Layer 1 at startup from `CLAUDE_MD_PATH` |
| `normalize_content()` | String or JetBrains block-array → plain text |
| `build_optimized_messages()` | Assemble layers 1–4 |
| `resolve_session_id()` | `X-Session-Id` header → per-session `SessionState` |
| `resolve_developer_id()` | `X-Developer-Id` or `TELEMETRY_DEVELOPER_ID` |
| `record_telemetry()` | Terminal report + append JSONL event |
| `dream_compact()` | Background Haiku ledger synthesis |
| `maybe_trigger_compaction()` | Turn-10 threshold |
| `proxy_messages()` | `POST /v1/messages` — sync path |
| `_handle_streaming()` | SSE forward when `stream: true` |

### Request flow

```
Claude CLI / JetBrains POST /v1/messages
  → resolve developer + session ids (headers / env)
  → normalize last user message (Layer 4)
  → build [L1, L2, L3..., L4]
  → AsyncAnthropic messages.create (or .stream)
  → record_exchange (append to Layer 3)
  → record_telemetry → stats/*.jsonl
  → maybe compact
  → return JSON or SSE
```

---

## 10. Deployment

> **Team rollout:** Modes A / C / D (offline corpus import) — no package install, no proxy. See [Usage.md](context-synthesizer/Usage.md).
> The proxy below is the **gateway implementation** the synthesizer optimizes toward; it is not part of the team workflow.

### Gateway implementation (venv — not team workflow)

```bash
cd ~/Out-of-bound-chronicles
python3 -m venv .venv
.venv/bin/pip install fastapi uvicorn anthropic httpx

export ANTHROPIC_API_KEY="sk-ant-your-team-key"
export CLAUDE_MD_PATH="context-synthesizer/Claude.md"   # or production path
export ANTHROPIC_MODEL="claude-sonnet-4-6"
export COMPACTION_MODEL="claude-haiku-4-5-20251001"

# Terminal 1 — proxy
.venv/bin/python context-synthesizer/proxy_tool.py

# Terminal 2 — verify Layer 1 size
.venv/bin/python context-synthesizer/count_tokens.py

# Terminal 3 — benchmark (optional)
.venv/bin/python context-synthesizer/test_simulator.py
```

### JetBrains configuration

| Setting | Value |
|---------|--------|
| API base URL | `http://127.0.0.1:8080` |
| Endpoint | `POST /v1/messages` |
| Session header | `X-Session-Id: developer-username` |

In IDE: `Settings → Tools → AI Assistant → Providers` → set Anthropic endpoint to `http://127.0.0.1:8080`.

### Claude CLI configuration

In `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8080",
    "TELEMETRY_DEVELOPER_ID": "developer-username"
  }
}
```

Stats collection workflow: [`CLI_STATS_GUIDE.md`](context-synthesizer/CLI_STATS_GUIDE.md).

### Planned: PyInstaller binary

```bash
# Not yet packaged — future distribution option
pyinstaller --onefile context-synthesizer/proxy_tool.py
```

```
┌──────────────────┐        ┌─────────────────────────┐        ┌─────────────────┐
│  JetBrains IDEA  │ ──────▶│  Context Synthesizer    │ ──────▶│  Anthropic API  │
│  (unchanged UX)  │  HTTP  │  proxy_tool.py :8080    │  TLS   │  (cache hits)   │
└──────────────────┘        └─────────────────────────┘        └─────────────────┘
```

---

## 11. Ecosystem Comparison

| Capability | `claude-devtools` | `rtk-ai/rtk` | **Context Synthesizer** |
|---|---|---|---|
| **Primary role** | Visual observability dashboard | Shell output compressor | API-layer context memory manager |
| **Operates on** | Local `~/.claude/` logs | Bash pipe outputs | Live HTTP API payloads |
| **Token strategy** | Visualizes degradation | Truncates CLI output | Caches static blocks; synthesizes history |
| **Active or passive** | Passive viewer | Active input filter | Active middleware |
| **IDE change** | None (companion app) | Terminal wrapper | URL redirect + optional session header |
| **Metrics** | Visual UI | No | Per-turn terminal audit + simulator rollup |

**Complementary chain:** `rtk` → **Context Synthesizer** → Anthropic API → `claude-devtools` for visual audit.

---

## 12. Comprehension Checkpoints

**Checkpoint 1: Cache-Busting Diagnosis**

A developer reports 0% cache efficiency. Their client prepends `internal_user_session_uuid` to `messages[0]`.

*Diagnosis:* Dynamic content at index 0 busts the entire prefix. **Fix:** keep `messages[0]` as static `Claude.md`; put session id in `X-Session-Id` header (as shipped).

---

**Checkpoint 2: Trigger Threshold Design**

Why might a pure turn-count trigger be insufficient?

*Answer:* Turn size varies — two turns with huge dumps can exceed 100K tokens before turn 10. **Shipped:** turn count only. **Planned:** `turns ≥ 10 OR history_tokens ≥ 100K`.

---

**Checkpoint 3: Multi-Breakpoint Caching**

```
Block 1: Claude.md (200K)    — cache_control: ephemeral
Block 2: State Ledger (500)  — cache_control: ephemeral
Block 3: Rolling turns (3K)  — no cache_control
Block 4: New prompt (40)     — no cache_control
```

*Answer:* Blocks 1–2 → `cache_read` / `cache_creation`. Blocks 3–4 → `input_tokens` only. Warm turn: ~200.5K @ $0.30/M + ~3K @ $3.00/M.

---

**Checkpoint 4: State Override Semantics**

Bad ledger: `- Database: was PostgreSQL, now MongoDB`  
Good ledger: `- Database layer: MongoDB — relational schema deprecated`

*Answer:* State Override rule — current truth only. **Partially shipped** in `dream_compact()` prompt; stricter validation planned.

---

*End of Report*

---

> **Repository:** `Out-of-bound-chronicles/context-synthesizer/`  
> **Key references:** [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) · `matt1398/claude-devtools` · `rtk-ai/rtk`  
> **Last aligned with codebase:** 2026-06-10

<!-- SOURCE: /home/harshil/Out-of-bound-chronicles/context_os_technical_report.md sha256:0f84d082da40 -->
