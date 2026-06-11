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
