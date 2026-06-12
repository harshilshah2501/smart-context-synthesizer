# Compaction Proof Report — Simple Explanation

**Date:** 2026-06-11  
**Session studied:** `ac4ecef7` (meet-chavda, CMDB research repo)  
**Focus turn:** **178** (largest context spike in the session)  
**Tools used:** `analyze_hot_session.py`, `analyze_claude_caching.py`, `compare_compaction.py` (Dreaming v4 + Haiku)

---

## Executive summary (read this first)

We took a **real 415-turn Claude Code session** and asked a practical question:

> *If we used a smart context synthesizer instead of keeping the full chat history, would context get much smaller — and would the model still know what matters?*

**Answer: yes on both counts, for this session.**

| What we measured | Result |
|------------------|--------|
| Full history size (naive) | ~**725,000** tokens |
| Synthesizer-shaped payload at turn 178 | ~**3,800** tokens |
| **Size reduction** | **~99.5%** |
| Haiku ledger quality | Captures phases, files, user corrections, open tasks |
| Claude Max caching today | Already **~99%** cache read — synthesizer is **not** mainly about “turning on caching” |

**In one sentence:** The synthesizer turns a huge transcript (full of bash logs and screenshot data) into a short project brief plus the last few turns — and Haiku’s ledger still remembers the important decisions.

---

## 1. What problem are we solving?

Long coding sessions grow like this:

```
Turn 1   → small context
Turn 50  → medium
Turn 178 → huge (tool output, images, repeated file reads)
Turn 415 → would be enormous if nothing is compacted
```

Claude Code already **caches** most of the prefix (cheap). But the session still accumulates **junk** in history: bash pipeline logs, base64 images, the same file read 21 times.

The **context synthesizer** is a different shape:

```
Layer 1  →  Rules (Claude.md)
Layer 2  →  Ledger (short project memory, updated by “Dreaming”)
Layer 3  →  Last ~10 turns only
Layer 4  →  Current user message
```

Instead of “remember every byte forever,” it keeps **a summary + a small recent window**.

---

## 2. The session we studied

| Fact | Value |
|------|-------|
| Project | `cmdb-research-repository` |
| User turns | 415 |
| Tool calls | 1,722 |
| Unique files touched | 234 |
| Native auto-compact (`/compact`) | **3 times** (rare) |
| Synthesizer would compact (every 10 turns) | **~41 times** (proactive) |

**Turn 178** is the worst spike: **40 tool calls**, mostly the agent reading **PNG screenshots** (printer UI) and dumping **base64 image data** into context — hundreds of thousands of characters of low-value payload.

---

## 3. Hot session analysis — what the numbers mean

From `analyze_hot_session.py` on this session:

| Label | Tokens (est.) | What it actually means |
|-------|---------------|-------------------------|
| **Real input** (last API call) | ~541K | What Claude Code **really sent** on the last turn (mostly cache read) |
| **Final naive est.** | ~926K | *Hypothetical:* “What if we kept **every** user/assistant/tool byte from all 415 turns in context at once?” |
| **Final synth est.** | ~23K | *Hypothetical:* “What if we used the four-layer synthesizer shape?” |
| **Compression est.** | 97.5% | Naive vs synth counterfactual — **not** a 97% bill reduction |

### Sparklines (growth over time)

```
naive: ▁▁▁▁▁▁▁▁▁▁▁▁▂▂▂▃▃▃▃▃▃▄▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▇▇▇▇▇█   ← keeps growing
synth: ▁▂▁▁▁▁▁▁▂▁▁▃▁▃▁▄▂▃▁▁▁█▃▃▁▂▂▂▅▁▁▁▁▁▁▁▁▁▁▁▁▁▁▅▃▁▁▁   ← stays mostly flat
```

**Plain English:** Without compaction, context climbs until it hits a wall. With the synthesizer shape, it stays bounded (with occasional spikes when the last-10-turns window contains a heavy turn).

### Top file re-reads (waste the synthesizer removes)

| File | Times read |
|------|------------|
| `Admin.tsx` | 21× |
| `a4_identification.py` | 14× |
| `RelationshipGraph.tsx` | 10× |

The ledger should keep **latest file state once**, not 21 copies in history.

### Tool mix (what Dreaming v4 targets)

| Tool | Share |
|------|------:|
| Bash | 39.7% |
| Edit | 33.5% |
| Read | 16.3% |

Rules: **collapse Bash output**, **dedupe Read snippets**, **keep latest edit per file**.

---

## 4. Native caching — why 97% compression ≠ 97% cost savings

From `analyze_claude_caching.py`:

| Signal | Value |
|--------|-------|
| Assistant messages with `cache_read` | **99.2%** |
| Hot session `ac4ecef7` at turn 415 | **99.3%** cache read |

**Plain English:** Claude Max **already** reuses a cached prefix on almost every API call. You are not trying to “enable caching.”

What you pay for on each call:

```
┌─────────────────────────────────────────┐
│  cache_read     ← cheap (~10× less)     │  ← 99% of volume today
├─────────────────────────────────────────┤
│  cache_write    ← prefix rebuilt        │  ← happens when history shifts
├─────────────────────────────────────────┤
│  uncached tail  ← new tokens each turn  │  ← small but important
└─────────────────────────────────────────┘
```

**Synthesizer value:**

1. **Context headroom** — avoid growing toward overflow  
2. **Less junk in the tail** — no base64 images and 30-line bash dumps in recent turns  
3. **Proactive memory** — ledger updated often, not 3 emergency compacts in 415 turns  

---

## 5. Compaction proof run (`compare_compaction.py`)

We replayed **Dreaming v4** with **Haiku** (`claude-haiku-4-5-20251001`): compact every 10 turns from turn 1 through 177, then compared shapes at **turn 178**.

### Size comparison at turn 178

| Payload | ~Tokens | vs naive |
|---------|--------:|----------|
| **Naive** (full history turns 1–178) | 724,562 | — |
| **Raw 10-turn window** (unprocessed) | 155,057 | — |
| **Preprocessed window** (v4 rules, no LLM) | 2,543 | **98.4% smaller** than raw window |
| **Haiku ledger** (turns 1–177 summarized) | ~877 | — |
| **Full synthesizer payload** (L1+L2+L3+L4) | 3,778 | **99.5% smaller** than naive |

*Token estimates use chars ÷ 4. Source: `stats/compare_compaction.json`.*

### Three layers of improvement

| Step | What happens | Analogy |
|------|----------------|---------|
| **1. Preprocessing** | Chop bash walls, trim tool blocks, dedupe paths | Throw away the receipt, keep the total |
| **2. Dreaming (Haiku)** | Merge old turns into ledger bullets | Write meeting notes instead of a full transcript |
| **3. Four-layer shape** | Ledger + last 10 turns + current question | Briefing doc + “what we just said” + your ask |

---

## 6. What each section of the output showed you

### NAIVE (last turns)

Raw turn 178: your printer identification question + agent **Read** of PNG files with **massive base64 blobs**. This is the bloat.

### RAW WINDOW (turns 169–178)

Ten turns of unfiltered chat: pipeline completion logs, docker commands, migration file writes, user saying “ok,” user pushing back on full-tree pull, then the printer bug report.

### PREPROCESSED WINDOW (same 10 turns, no LLM)

Same story, **98% shorter**:

- Bash → a few lines + “truncated”
- Long Write blocks → shortened
- You still see: pipeline done, Step 6/7, empty metadata tabs, user angry about pulling all 1,294 classes, printer UI issue

### LEDGER (after Haiku replay)

A **project brief**, not chat logs. Haiku preserved:

**Phase 1 delivered**

- Tree UI, 7 tabs, gradient fixes  
- Commit `f0066b2`  
- Key files: `index.css`, `HierarchyTree.tsx`, design docs locked  

**Phase 2 scope (4 decisions)**

- `--scope=class` vs `--scope=subtree`  
- `python -m pipeline.orchestrator all --anchor cmdb_ci`  
- Metadata discovery rules  
- Validation bar same as Phase 1  

**Pipeline built (Steps 2–6)**

- Class info, reconciliation, lookups, 4366 CI instances, relationships  
- Migrations 0004–0009 applied  

**Critical user correction (captured)**

> User flagged full-tree metadata pull as overkill. Scope reset: **one anchor class + direct children only**, not all 1,294 classes. Runaway orchestrator killed.

**Open tasks**

- Scoped metadata agents  
- Instance relationships validation  
- Re-test UI on a single branch (`cmdb_ci_printer`)  
- Lock `docs/03-phase-2-scope.md`  

### SYNTHESIZER-SHAPED PAYLOAD

What production would send:

1. **Layer 1** — rules (`Claude.md`)  
2. **Layer 2** — ledger above (~3.5K chars)  
3. **Layer 3** — preprocessed last ~10 turns  
4. **Layer 4** — turn 178 user message (printer identification + screenshot refs)  

Total ~3.8K tokens vs ~725K naive.

---

## 7. What this proves — and what it does not

### Proven (this session)

| Claim | Evidence |
|-------|----------|
| Context can be **much** smaller | 99.5% reduction at turn 178 |
| Bloat is **real and identifiable** | Base64 images, bash logs, 40 tools on one turn |
| Preprocessing alone helps a lot | 98.4% on the 10-turn window |
| Haiku ledger keeps **useful facts** | Phases, files, migrations, user correction, open tasks |
| Native compact is **too rare** | 3× auto-compact vs ~41 synthesizer triggers |

### Not proven yet

| Claim | Why |
|-------|-----|
| Bill drops 99% | Caching already absorbs most input cost |
| Model answers **equally well** on live tasks | We replayed offline; no A/B on live coding |
| Ledger is perfect on every session | One session, one turn deep-dived |
| Works on Cursor the same way | Cursor lacks per-turn API usage in logs |

---

## 8. Synthesizer vs Claude `/compact`

| | Claude `/compact` | Synthesizer Dreaming v4 |
|--|-------------------|-------------------------|
| **When** | User runs it, or late auto (3× here) | Every 10 turns + token threshold |
| **Output** | Opaque session summary | Structured **ledger** (files, decisions, tasks) |
| **Code-aware** | Generic | Bash collapse, Read dedup, latest file state |
| **This session** | Almost never ran | Would run **41×** |

The synthesizer is **proactive architectural memory**, not an emergency overflow button.

---

## 9. Verdict

| Question | Answer |
|----------|--------|
| Is there visible improvement? | **Yes** — 725K → 3.8K tokens at the worst spike |
| Is the improvement meaningful? | **Yes** — removes image/base64/bash noise, keeps project story |
| Is ledger quality acceptable? | **Yes for this session** — phases, scope, correction, open work preserved |
| Ready for weekly team corpus? | **Optional** — use weekly export for regression **after** you trust this; not required to believe the initial proof |
| Ready for live gateway? | **Needs pilot** — one dev on `proxy_tool.py` with BYOK API key |

**Confidence level for this session: high on size; good on ledger content; live quality still needs a small pilot.**

---

## 10. How to reproduce

```bash
cd ~/Out-of-bound-chronicles

# 1. Hot session overview
.venv/bin/python context-synthesizer/analyze_hot_session.py \
  --source claude --largest \
  --cli-root context-synthesizer/stats/backups/meet-chavda/.claude/projects \
  --export context-synthesizer/stats/hot_review.json

# 2. Native caching
.venv/bin/python context-synthesizer/analyze_claude_caching.py \
  --cli-root context-synthesizer/stats/backups/meet-chavda/.claude/projects

# 3. Compaction proof (offline — preprocessing only)
.venv/bin/python context-synthesizer/compare_compaction.py \
  --session ac4ecef7 --turn 178

# 4. Compaction proof (full Haiku ledger replay)
export ANTHROPIC_API_KEY=...
.venv/bin/python context-synthesizer/compare_compaction.py \
  --session ac4ecef7 --turn 178 --run-dreaming --haiku
```

**Outputs**

| File | Contents |
|------|----------|
| `stats/hot_review.json` | Hot session metrics |
| `stats/compare_compaction.json` | Turn 178 comparison + full ledger text |

**Cheaper Haiku test (1 batch only):**

```bash
.venv/bin/python context-synthesizer/compare_compaction.py \
  --turn 178 --run-dreaming --haiku --dreaming-batches 1
```

---

## 11. Suggested next steps

1. **Read the ledger** in `stats/compare_compaction.json` — confirm it matches your memory of the project.  
2. **Spot-check another spike** — turn 94 (+38K) or turn 235 (+66K):  
   `compare_compaction.py --turn 94 --run-dreaming --haiku`  
3. **Optional live pilot** — one developer routes through `proxy_tool.py` for a week (BYOK).  
4. **Weekly corpus** — only when you want regression tracking across sessions (`DEPLOY.md`).

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md) | meet-chavda vs chandresh vs om (Phase 2 validation) |
| [SYNTHESIZER_RND_REPORT.md](SYNTHESIZER_RND_REPORT.md) | Full R&D record |
| [DEPLOY.md](../guides/DEPLOY.md) | Weekly export playbook (monitoring, not initial proof) |
| [README.md](../../context-synthesizer/README.md) | Toolkit overview |
| [MEET_CHAVDA_CORPUS_REPORT.md](MEET_CHAVDA_CORPUS_REPORT.md) | Full meet-chavda corpus (32 sessions) |
| [OM_CORPUS_REPORT.md](OM_CORPUS_REPORT.md) | om turn-100 proof (99.5%) |
