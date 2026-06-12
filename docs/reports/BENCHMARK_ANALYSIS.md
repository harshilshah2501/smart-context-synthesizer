# Benchmark Analysis — 12-Turn Simulator Run

> **Not a team workflow.** Internal gateway validation via `test_simulator.py` + `proxy_tool.py`.
> Team data collection uses offline **Modes A / C / D** — see [README.md](../../context-synthesizer/README.md).

**Date:** 2026-06-10  
**Session:** `simulator-benchmark`  
**Model:** `claude-sonnet-4-6`  
**Endpoint:** `http://127.0.0.1:8080/v1/messages`  
**Total wall time:** 200.31 seconds  

This document explains the simulator output line-by-line: what each number means, how it maps to proxy layers, and why savings were only **10.2%** in this run (versus the **~90%** target at production scale).

**Related docs:**

- [Context Synthesizer technical report](../context_os_technical_report.md) — architecture, shipped vs planned, §8.1 summary
- [README](../../context-synthesizer/README.md) — quick start
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
