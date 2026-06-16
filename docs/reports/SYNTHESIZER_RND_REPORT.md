# Context Synthesizer — R&D Report

> **Rollout doc:** This report is the R&D record. For Motadata team install (live proxy, dashboard, SharePoint), use **[DEVELOPER_ONBOARDING.md](../guides/DEVELOPER_ONBOARDING.md)** and **[TEAM_ANNOUNCEMENT.md](../guides/TEAM_ANNOUNCEMENT.md)**.

**Date:** 2026-06-10 (updated 2026-06-16)  
**Status:** Phase 1–3 complete — live proxy + dashboard + SharePoint deploy live  
**Audience:** Team leads, infrastructure engineers, future maintainers  

This document captures the full arc of the Context Synthesizer project: goals, architecture, data-collection strategy, empirical findings from real developer sessions, and the strategic conclusion that **optimization lives in history shape—not in enabling prompt caching**.

**Companion docs:**

| Doc                                                                 | Contents                                         |
| ------------------------------------------------------------------- | ------------------------------------------------ |
| [README.md](../../context-synthesizer/README.md)                    | Quick start, env vars, file index                |
| [Usage.md](../guides/Usage.md)                                         | Offline corpus modes (A/C/D)                     |
| [BENCHMARK_ANALYSIS.md](BENCHMARK_ANALYSIS.md)              | 12-turn proxy simulator, cost bifurcation        |
| [CLI_STATS_GUIDE.md](../guides/CLI_STATS_GUIDE.md)                     | Mode A import details                            |
| [DEVELOPER_ONBOARDING.md](../guides/DEVELOPER_ONBOARDING.md)         | **Team rollout** — live proxy + dashboard        |
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

The **Context Synthesizer** is a toolkit for **smart context compaction**. It ships a **live proxy** (`proxy_tool.py`) for Claude Code sessions plus **offline R&D modes** (A, C, D) that import long IDE sessions, measure native token usage, and estimate how much smaller a **four-layer gateway payload** would be.

**Key finding from real developer data (three corpora — see [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md)):**

meet-chavda (32 sessions, 859 turns):

| Metric                              | Native Claude Code               | Synthesizer opportunity                                           |
| ----------------------------------- | -------------------------------- | ----------------------------------------------------------------- |
| Cache read rate (warm turns)        | **~99%** on assistant messages   | Already solved — not our lever                                    |
| Hot-session input prefix (turn 415) | **541K tokens** cumulative       | Counterfactual **~23K** shaped payload (**97.5%** char reduction) |
| Cache writes per long session       | **407 turns** with `cache_write` | Smaller, stabler prefix → fewer write spikes                      |
| File re-reads                       | `Admin.tsx` read **21×**         | Code-aware ledger keeps latest state only                         |
| Tool bloat                          | **684 Bash**, **280 Read** calls | Collapse tool output in ledger                                    |

**Bottom line:** Claude Code already caches brilliantly. Our value is as a **history architect**—shrinking and stabilizing what gets cached—not as a caching enabler.

**Team workflow (Motadata rollout):** SharePoint package → `bash run-setup.sh firstname.lastname` → live compaction proxy (default) + optional Monday corpus export. No git, no per-dev API key. See [DEVELOPER_ONBOARDING.md](../guides/DEVELOPER_ONBOARDING.md).

**Offline R&D workflow:** Mode **D** (Claude Max), **Mode C** (Cursor), or **Mode A** (Claude Code import) — see [Usage.md](../guides/Usage.md).

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

| OS concept                       | Synthesizer layer            |
| -------------------------------- | ---------------------------- |
| Page cache (stable, reusable)    | Layer 1 + Layer 2            |
| Working RAM (sliding window)     | Layer 3                      |
| Swap / GC (background synthesis) | Dreaming compaction → ledger |

### Dreaming (compaction)

When `turn_number % MAX_TURNS_THRESHOLD == 0` (default **10**), a background Haiku call (`COMPACTION_MODEL`) synthesizes rolling turns into the history ledger, then clears the rolling window. Ledger mutation is the only intentional cache-bust on Layer 2.

### Ecosystem position

```
JetBrains / Claude CLI → [rtk-ai/rtk] → Context Synthesizer → Anthropic → [claude-devtools]
```

| Tool                    | Role                                                      |
| ----------------------- | --------------------------------------------------------- |
| `rtk-ai/rtk`            | Compress terminal output before it enters context         |
| **Context Synthesizer** | Structure API payload, cache `Claude.md`, compact history |
| `claude-devtools`       | Visualize session logs after the fact                     |

---

## 4. Project Evolution

| Phase                       | Decision                                                                                     |
| --------------------------- | -------------------------------------------------------------------------------------------- |
| **Initial goal**            | Ubuntu `.deb` for JetBrains team with shared API gateway                                     |
| **Pivot**                   | Team uses **Claude Max subscription**, not BYOK — live proxy not viable for most devs        |
| **Dropped**                 | **Ubuntu `.deb` rollout** — no team-wide package install; `packaging/` kept as unused legacy |
| **Revised goal**            | Build a **smart, code-aware synthesizer** using offline session analysis                     |
| **Vendor-agnostic gateway** | Discussed and **de-prioritized** — focus is synthesizer R&D, not multi-vendor routing        |
| **Cursor support**          | Live proxy not possible; **Mode C** imports `~/.cursor/projects/**/agent-transcripts/`       |
| **Delivery today**          | Python scripts + venv; weekly corpus export (Modes A / C / D)                                |

---

## 5. Data Collection Modes

| Mode  | Source                                              | API key? | Token bifurcation            | Primary use                          |
| ----- | --------------------------------------------------- | -------- | ---------------------------- | ------------------------------------ |
| **A** | `import_cli_logs.py` — Claude CLI assistant turns   | No       | Yes (per turn)               | Default weekly token snapshot        |
| **C** | `import_cursor_sessions.py` — Cursor transcripts    | No       | Estimates only               | Cursor long-session R&D              |
| **D** | `import_claude_sessions.py` — `~/.claude/projects/` | No       | **Yes** + session aggregates | **Claude Max / Pro synthesizer R&D** |

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

| Metric           | Value         |
| ---------------- | -------------:|
| Wall time        | 200.31 s      |
| Uncached input   | 22,715 tokens |
| Cache read       | 16,202 tokens |
| Cache write      | 15,755 tokens |
| Output           | 10,010 tokens |
| Baseline cost    | $0.3142       |
| Realized cost    | $0.2822       |
| **Savings**      | **10.2%**     |
| Cache efficiency | 29.6%         |

### Why only 10.2% (not ~90%)

Starter `Claude.md` is **below Sonnet 4.6’s 1,024-token minimum** per `cache_control` block. Cache-eligible prefix was ~2.5K tokens, not 200K. Uncached Layer 3+4 dominated spend.

**Conclusion:** Proxy layout behaved correctly (cache engaged turn 4+, reads climbed turns 6–10, compaction at turn 10, cache bust on turn 11 massive prompt). **The bifurcation works; the corpus is not production-sized.**

Full turn-by-turn narrative: [BENCHMARK_ANALYSIS.md](BENCHMARK_ANALYSIS.md).

---

## 7. Developer Corpus: meet-chavda

**Source:** `context-synthesizer/claude-folder-backup.zip`  
**Extracted to:** `stats/dev-backup/.claude/projects/`  
**Developer:** meet-chavda  

### Corpus summary

| Metric                    | Value                                               |
| ------------------------- | ---------------------------------------------------:|
| Sessions                  | 32                                                  |
| User turns                | 859                                                 |
| Assistant API messages    | 8,173                                               |
| Models                    | `claude-opus-4-7`, `claude-opus-4-8`, `<synthetic>` |
| Sessions with token usage | 27 / 32                                             |

### Top sessions by synthesizer savings potential

| Session      | Turns | Real tokens | Synth est | Save %    | Tools | Cache % |
| ------------ | -----:| -----------:| ---------:| ---------:| -----:| -------:|
| **ac4ecef7** | 415   | 542,858     | 22,850    | **97.5%** | 1,722 | 99.3%   |
| 4e961ee7     | 89    | 504,347     | 25,044    | 87.0%     | 628   | 51.4%   |
| f0b1556a     | 84    | —           | 1,849     | 99.2%     | 620   | 0.0%    |
| 64518332     | 48    | 98,645      | 8,040     | 74.2%     | 9     | 96.7%   |
| 9fd659d0     | 45    | 567,501     | 810,346   | 31.0%     | 382   | 99.2%   |

**Note:** Negative or low save % on short sessions is expected—the synthesizer overhead (ledger + window) can exceed naive history when sessions are brief. Value concentrates in **long, tool-heavy sessions**.

**Outputs:**

- `stats/meet-chavda_corpus.jsonl` (32 session summaries)
- `stats/meet-chavda_corpus.csv`
- `stats/meet-chavda_hot_ac4ecef7.json` (deep dive export)

### Per-developer corpus reports

| Developer | Report | Hot session | Turns | Compression | Spike-turn proof |
|-----------|--------|-------------|------:|------------:|-----------------:|
| meet-chavda | [MEET_CHAVDA_CORPUS_REPORT.md](MEET_CHAVDA_CORPUS_REPORT.md) | `ac4ecef7` | 415 | 97.5% | turn 178: **99.5%** |
| chandresh | [CHANDRESH_CORPUS_REPORT.md](CHANDRESH_CORPUS_REPORT.md) | `d326033e` | 28 | 68.9% | turn 23: **95.2%** |
| om | [OM_CORPUS_REPORT.md](OM_CORPUS_REPORT.md) | `dcb92020` | 120 | 90.9% | turn 100: **99.5%** |

Full three-way comparison: [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md).

---

## 8. Native Claude Code Caching Analysis

Tool: `analyze_claude_caching.py --cli-root <path>`

### Corpus-wide (meet-chavda, 32 sessions)

| Metric                                | Value                     |
| ------------------------------------- | -------------------------:|
| User turns with `cache_read > 0`      | 771 / 859 (**89.8%**)     |
| User turns with `cache_write > 0`     | 774 / 859 (**90.1%**)     |
| Turns with **no** cache signal        | 84 / 859 (9.8%)           |
| Assistant msgs with `cache_read > 0`  | 8,107 / 8,173 (**99.2%**) |
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

| Aspect             | Behavior                                                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Primary mode**   | **User-triggered** — developer runs `/compact` when context feels heavy or UI hints appear                                           |
| **Secondary mode** | **Auto-compact** — fires only when the session approaches the model context ceiling (reactive, not proactive)                        |
| **What it does**   | Summarizes conversation history, inserts a `compact_boundary` in session logs, replaces most prior turns with a continuation summary |
| **Goal**           | Avoid `context exceeded` / `prompt_too_long` — **fit in the window**, not optimize cost per turn                                     |
| **Enforcement**    | **Weak by design** — history keeps growing turn-by-turn until pressure mounts                                                        |

**Evidence from meet-chavda hot session (415 turns):**

| Compaction type                                  | Count           | Implication                                         |
| ------------------------------------------------ | ---------------:| --------------------------------------------------- |
| Claude auto-compact (`compact_boundary` in logs) | **3**           | Native compact ran rarely — ~0.7% of turns          |
| Synthesizer triggers (@ 10-turn threshold)       | **41**          | Proactive compaction would have run ~10× more often |
| Final input prefix                               | **541K tokens** | Native compact did **not** prevent prefix bloat     |

So on long, tool-heavy sessions Claude Code **allows history to grow** (cached at ~99% read, but still huge). Developers must **choose** to `/compact`, or wait until auto-compact fires near the limit. It is **not** an always-on, turn-by-turn history architect.

**Why our synthesizer still matters:**

```
Claude /compact     →  "We're about to overflow — emergency summarize"
Synthesizer Dreaming →  "Every N turns / N tokens — merge into cached ledger"
```

|                       | Claude `/compact`            | Synthesizer Dreaming v4                            |
| --------------------- | ---------------------------- | -------------------------------------------------- |
| Trigger               | Manual or late auto          | Turn threshold **or** token threshold (proactive)  |
| Output                | Opaque session summary       | Structured **Layer 2 ledger** with `cache_control` |
| Code-aware            | Generic continuation summary | File latest-state, Bash collapse, Read dedup       |
| Frequency on ac4ecef7 | 3×                           | Would be 41× (turn-based) + token spikes           |

Plugin **`PreCompact` hooks** (see Claude plugin-dev docs) let extensions inject “preserve this” text **before** native compact runs—they do not replace `/compact` and are unrelated to our proxy.

---

## 9. Hot Session Deep Dive: ac4ecef7

**Project:** `cmdb-research-repository`  
**Session ID:** `ac4ecef7-10f7-4a50-89c4-dcf30b7219ce`  
**Duration:** 415 user turns, 3,410 assistant messages  

### Token usage (final turn, cumulative from CLI logs)

| Metric                                      | Value               |
| ------------------------------------------- | -------------------:|
| Total input                                 | 541,343             |
| Cache read                                  | 537,417 (**99.3%**) |
| Output                                      | 716,416             |
| Tool calls                                  | 1,722               |
| Unique file paths                           | 234                 |
| Claude `/compact` (auto only; see §8.1)     | 3                   |
| Synthesizer compaction triggers (@ turn 10) | 41                  |

### Context growth

| Estimate                   | Tokens    |
| -------------------------- | ---------:|
| Final naive (full history) | 926,162   |
| Final synthesizer-shaped   | 22,850    |
| **Compression**            | **97.5%** |

Sparkline pattern: naive grows monotonically (`▁…█`); synthesizer stays flat with periodic compaction spikes.

### Top growth spikes

| Turn | Δ tokens | Tools | Notes                                         |
| ---- | -------- | -----:| --------------------------------------------- |
| 178  | +123,713 | 40    | Largest spike — candidate for dump compaction |
| 235  | +66,586  | 20    | Heavy assistant/tool output                   |
| 372  | +40,266  | 3     | Large assistant block                         |
| 94   | +38,323  | 55    | Early heavy tool burst                        |

Turn 96 in caching trace showed **+511K `cache_write`** — prefix rebuild after context shift.

### Top file re-reads

| File                                            | Reads | Turn range |
| ----------------------------------------------- | -----:| ---------- |
| `frontend/src/pages/Admin.tsx`                  | 21    | 219–415    |
| `backend/pipeline/agents/a4_identification.py`  | 14    | 94–378     |
| `frontend/src/components/RelationshipGraph.tsx` | 10    | 94–409     |
| `backend/pipeline/orchestrator.py`              | 10    | —          |

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

| Session  | Turns | Naive est | Synth est | Save % | Tools |
| -------- | -----:| ---------:| ---------:| ------:| -----:|
| e64142ab | 377   | 610,909   | 4,316     | 99.3%  | 3,286 |
| 511d5225 | 191   | 401,791   | 7,380     | 98.2%  | 1,712 |
| fb6a3cda | 147   | 117,442   | 8,937     | 92.4%  | 826   |

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

| Scenario                                   | Room to optimize?                   |
| ------------------------------------------ | ----------------------------------- |
| Improve cache read % (99% → 100%)          | **Tiny**                            |
| Shrink 541K input prefix on long sessions  | **Large**                           |
| Cut `cache_write` spikes on history growth | **Real**                            |
| Dedupe 21× file reads into ledger state    | **Real**                            |
| Short sessions (<10 turns)                 | **Small**                           |
| Output token cost                          | **Out of scope** (model generation) |

### Two optimization axes (do not conflate)

| Axis                  | Question                           | Owner today             | Our role       |
| --------------------- | ---------------------------------- | ----------------------- | -------------- |
| **Cache utilization** | “Is the prefix served from cache?” | Claude Code (~99%)      | None needed    |
| **Cache payload**     | “How big is the prefix?”           | Grows with full history | **Core value** |

---

## 12. Economics Worked Example

### Hot session turn 415 — same 99% cache read, different prefix size

Anthropic prompt caching (Sonnet-class, illustrative):

| Bucket         | Rate (/1M) |
| -------------- | ---------- |
| Uncached input | $3.00      |
| Cache read     | $0.30      |
| Cache write    | $3.75      |

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

| Field                                               | Use                                               |
| --------------------------------------------------- | ------------------------------------------------- |
| `usage` / `cost`                                    | Uncached vs cache read vs cache write + savings % |
| `context.est_layer1_tokens` … `est_prompt_tokens`   | Per-layer size estimates                          |
| `context.client_message_count` / `ignored_messages` | IDE history bloat stripped                        |
| `synthesis.uncached_tail_pct`                       | % of input at full price — **lower is better**    |
| `synthesis.client_bloat_ratio`                      | IDE msgs ÷ optimized payload                      |
| `source: compaction`                                | Haiku cost + `ledger_delta_chars`                 |

### Target signals (production `Claude.md` ~200K)

| Signal                           | Target                                      |
| -------------------------------- | ------------------------------------------- |
| `cache_read_pct`                 | **60%+**                                    |
| `uncached_tail_pct` (warm turns) | **<15%**                                    |
| `client_bloat_ratio`             | **5×+**                                     |
| Compaction `ledger_delta_chars`  | **Negative** (ledger shrinks or stays flat) |

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

| Component                                | Location                                        |
| ---------------------------------------- | ----------------------------------------------- |
| Four-layer index-aligned payload         | `proxy_tool.py`                                 |
| Live proxy + systemd user service        | `proxy_tool.py`, `install_proxy_service.sh`     |
| Live dashboard (billing bifurcation)     | `dashboard_api.py`, `static/dashboard.html`     |
| Dashboard token auth (WSL)               | `dashboard_auth.py`, `DASHBOARD_TOKEN` in `.env`  |
| Per-session `X-Session-Id`               | `resolve_session_id()`                          |
| Async + streaming                        | `AsyncAnthropic`, `_handle_streaming()`         |
| Dreaming @ turn 10                       | `maybe_trigger_compaction()`, `dream_compact()` |
| Bifurcated telemetry + synthesis metrics | `telemetry.py`                                  |
| 12-turn simulator                        | `test_simulator.py`                             |
| Mode A/C/D importers                     | `import_*.py`                                   |
| Hot session analyzer                     | `analyze_hot_session.py`                        |
| Native caching analyzer                  | `analyze_claude_caching.py`                     |
| Team stats rollup                        | `collect_stats.py`                              |
| Dreaming v4 + token/turn compaction      | `compaction.py`, `proxy_tool.py`                |
| SharePoint package + `run-setup.sh`      | `packaging/build-release-tarball.sh`            |
| `scripts/import_claude_backup.sh`        | One-command unzip + import pipeline           |
| `scripts/weekly_sync.sh`                 | Developer weekly export + upload              |
| `scripts/team_rollup.sh`                 | Team lead aggregation                         |
| `DEPLOY.md` + `DEVELOPER_ONBOARDING.md`  | Motadata rollout guides                       |

### Planned (pre-production)

| Item                                 | Notes                                         |
| ------------------------------------ | --------------------------------------------- |
| Full ~200K production `Claude.md`    | Team architecture corpus; starter ~380 tokens |
| Phase 2 benchmark with production L1 | Re-run `test_simulator.py`                    |

---

## 16. Next Steps: Implement, Test, Deploy

Ordered workstream after this report:

### Phase 1 — Implement smart synthesis *(done)*

1. **Dreaming v4 prompt** — `compaction.py`
2. **Token-based compaction** — `COMPACTION_TOKEN_THRESHOLD`
3. **Production L1 builder** — `build_production_claude_md.py`
4. **Layer 3 cap** — `MAX_LAYER3_TURNS`

### Phase 2 — Test (corpus-first) *(done — see [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md); re-run via `run_phase2_validation.py`)*

1. ~~`import_claude_sessions.py` on team backups~~ — **0 regression drift** vs `meet-chavda_corpus.jsonl`.
2. ~~`analyze_hot_session.py` on 100+ turn sessions~~ — Claude `ac4ecef7` 97.5%; Cursor 6/8 ≥90%.
3. ~~`analyze_claude_caching.py`~~ — **99.2%** assistant-msg cache_read; hot session **99.3%**.
4. ~~`collect_stats.py` corpus insights~~ — 40 sessions; 100+ turn avg save **93.5%**.
5. *(Optional)* `test_simulator.py` — skipped (no API key).
6. **Repeatable runner:** `run_phase2_validation.py`.

### Phase 3 — Deploy (corpus-first, no package) *(done — see `DEPLOY.md`)*

1. ~~**Max / Pro devs:** Mode D weekly export~~ → `scripts/export_weekly_corpus.sh --mode d`
2. ~~**Cursor devs:** Mode C~~ → `export_weekly_corpus.sh --mode cursor --project <slug>`
3. ~~**Team lead:** aggregate~~ → `scripts/team_rollup.sh` (+ optional `--validate`)
4. **One-time setup:** `scripts/setup.sh`
5. **Backup import:** `scripts/import_claude_backup.sh <zip>`

### Success criteria (Phase 2)

| Metric                | Target                                 | Source                               |
| --------------------- | -------------------------------------- | ------------------------------------ |
| Compression est.      | ≥90% on 100+ turn sessions             | Mode D `extra.compression_ratio_est` |
| File re-reads         | Declining in hot-session reports       | `analyze_hot_session.py`             |
| Native `cache_read` % | High on warm turns (baseline OK)       | Mode D / `analyze_claude_caching.py` |
| Corpus regression     | Stable week-over-week on same sessions | `import_claude_sessions.py`          |

---

## 17. Repository Reference

### Core gateway

| File            | Purpose                                            |
| --------------- | -------------------------------------------------- |
| `proxy_tool.py` | FastAPI gateway `:8080`, session state, compaction |
| `telemetry.py`  | Cost math, `ContextSnapshot`, `SynthesisMetrics`   |
| `models.py`     | Model ID registry                                  |
| `Claude.md`     | Layer 1 rules (replace for production)             |

### Analysis pipeline

| File                                  | Purpose                              |
| ------------------------------------- | ------------------------------------ |
| `import_claude_sessions.py`           | Mode D — Claude Max corpus           |
| `import_cursor_sessions.py`           | Mode C — Cursor transcripts          |
| `import_cli_logs.py`                  | Mode A — default Claude CLI import   |
| `analyze_hot_session.py`              | Single-session deep dive             |
| `analyze_claude_caching.py`           | Native caching behavior              |
| `collect_stats.py`                    | Team aggregate + tuning insights     |
| `run_phase2_validation.py`            | Repeatable Phase 2 corpus test suite |
| `claude_parse.py` / `cursor_parse.py` | Shared transcript parsers            |
| `session_models.py`                   | `SessionAnalysis`, `TurnSnapshot`    |

### Test & ops

| File                            | Purpose                                |
| ------------------------------- | -------------------------------------- |
| `test_simulator.py`             | 12-turn JetBrains client simulator     |
| `count_tokens.py`               | Layer 1 token budget verifier          |
| `build_production_claude_md.py` | Assemble Layer 1 from markdown sources |

### Data artifacts (gitignored except samples)

| Path                                  | Contents                        |
| ------------------------------------- | ------------------------------- |
| `claude-folder-backup.zip`            | meet-chavda backup (source)     |
| `stats/dev-backup/`                   | Extracted `~/.claude/projects/` |
| `stats/meet-chavda_corpus.jsonl`      | 32-session corpus               |
| `stats/meet-chavda_hot_ac4ecef7.json` | Hot session export              |

### Commands cheat sheet

```bash
# Mode A — default Claude CLI import
.venv/bin/python context-synthesizer/import_cli_logs.py --output stats/baseline.jsonl

# Mode D — Claude Max corpus
.venv/bin/python context-synthesizer/import_claude_sessions.py --developer meet-chavda --min-turns 25
.venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --largest
.venv/bin/python context-synthesizer/analyze_claude_caching.py --cli-root stats/dev-backup/.claude/projects

# Cursor corpus
.venv/bin/python context-synthesizer/import_cursor_sessions.py --project m-coder --min-turns 25

```

---

## 18. Glossary

| Term               | Definition                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------ |
| **Bifurcation**    | Splitting input cost into uncached / cache read / cache write buckets                      |
| **Cache read**     | Prefix served from Anthropic prompt cache ($0.30/M)                                        |
| **Cache write**    | Prefix stored into cache ($3.75/M) — cold start or bust                                    |
| **Dreaming**       | Background Haiku compaction of rolling turns into ledger                                   |
| **`/compact`**     | Claude Code built-in slash command — user-triggered summary; rare late auto-compact (§8.1) |
| **History ledger** | Layer 2 synthesized architectural state                                                    |
| **Mode A**         | Default Claude CLI log import (`import_cli_logs.py`)                                       |
| **Mode C**         | Offline Cursor transcript import                                                           |
| **Mode D**         | Enriched Claude Max / Pro corpus import                                                    |
| **Naive context**  | Full cumulative transcript size (counterfactual without synthesizer)                       |
| **Uncached tail**  | Tokens after last `cache_control` breakpoint (`input_tokens`)                              |
| **Warm turn**      | Request where `cache_read_input_tokens > 0`                                                |

---

*Report generated from engineering sessions, proxy benchmarks, and meet-chavda / m-coder corpus analysis. For questions or updates, extend this file rather than scattering findings across chat logs.*
