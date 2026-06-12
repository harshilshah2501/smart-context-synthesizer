# Om Corpus Report — Org Management prototype session

**Date:** 2026-06-12  
**Source:** `dcb92020-2f81-447f-8ace-a90d43b8793e.jsonl` (repo root export)  
**Developer:** om (om-vekariya)  
**Project:** Org Management UI (`~/Downloads/Org Mgmt`) — React/JSX MSP org-management prototype from Anthropic design + PRD

---

## Executive summary

Om’s corpus is a **single long session** (120 turns) — a middle ground between meet-chavda’s marathon (415 turns) and chandresh’s short-session zip (max 28 turns).

| | meet-chavda | chandresh | **Om (this session)** |
|--|-------------|-----------|------------------------|
| Sessions | 32 | 99 | **1** |
| Longest session | 415 turns | 28 turns | **120 turns** |
| Session compression est. | 97.5% | 68.9% | **90.9%** |
| Turn-level cache_read | ~90% | ~47% | **94.2%** |
| Tool profile | Bash + Edit | Read + Edit + Java | **Edit-heavy UI** (51%) |
| Best turn-level proof | turn 178: **99.5%** | turn 23: **95.2%** | turn 100: **99.5%** |

**Plain English:** Om built a large React prototype over 120 turns with heavy file editing and re-reads. Claude already caches ~99.8% of input on the last turn, but a **counterfactual full transcript** would be ~347K tokens vs ~32K synthesizer-shaped — and at spike turns the savings hit **~99%**.

---

## Import

This corpus arrived as one transcript file (not a zip). Place it under the standard backup layout, then import Mode D:

```bash
mkdir -p context-synthesizer/stats/backups/om/.claude/projects/-home-om-vekariya-Downloads-Org-Mgmt
cp dcb92020-2f81-447f-8ace-a90d43b8793e.jsonl \
  context-synthesizer/stats/backups/om/.claude/projects/-home-om-vekariya-Downloads-Org-Mgmt/

cd context-synthesizer
../.venv/bin/python import_claude_sessions.py \
  --cli-root stats/backups/om/.claude/projects \
  --developer om --min-turns 1 \
  --output stats/weekly/2026-06-12_om_claude_backup.jsonl \
  --export stats/weekly/2026-06-12_om_claude_backup.csv
```

**Outputs:**

| File | Description |
|------|-------------|
| `stats/backups/om/.claude/projects/.../dcb92020....jsonl` | Session transcript |
| `stats/weekly/2026-06-12_om_claude_backup.jsonl` | Mode D corpus (1 row) |
| `stats/om_hot_dcb92020.json` | Hot session deep dive |

---

## Session overview (`dcb92020`)

| Metric | Value |
|--------|------:|
| User turns | 120 |
| Assistant messages | 1,494 |
| Tool calls | 838 |
| Unique files | 47 |
| Model | `claude-opus-4-7` |
| Real input tokens (last turn) | 559,626 |
| Cache read | 558,412 (**99.8%**) |
| Output tokens | 419,211 |
| Naive est. → Synth est. | 346,770 → 31,694 tokens (**90.9%**) |
| Native auto-compact | **1×** |
| Synthesizer triggers @ turn 10 | **12×** (turns 10–120) |

**Task shape:** Fetch design spec → gap analysis vs PRD → implement/fix UI across tabs (Settings, Branding, Sites, Lifecycle, v1.5 features, whitelabel portals).

---

## Context growth

```
naive: ▁▁▁▂▂▂▂▂▂▂▂▂▃▃▃▃▃▃▃▃▃▃▃▃▃▄▄▄▄▅▅▅▅▅▅▅▅▅▆▆▆▆▇▇▇▇▇█
synth: ▁▂▂█▇▆▆▁▁▁▁▁▁▁▁▂▂▂▂▁▁▁▁▁▁▅▅▅▅▁▁▁▁▂▁▁▂▂▃▃▄▄▅▅▄▄▄▄
```

Synthesizer-shaped context stays mostly flat; naive history climbs steadily after turn 8 and again around turns 63–110.

---

## Top growth spikes

| Turn | Δ tokens (est.) | Tools | What happened |
|------|----------------:|------:|---------------|
| **8** | +52,869 | 68 | Early implementation burst — PRD gap fixes, mass Read/Edit across `data.js`, tabs |
| **63** | +44,789 | 3 | Large assistant payload (screenshot path / layout margin discussion) |
| **100** | +25,392 | 58 | v1.5 / offboarding / grep sweep across JSX |
| 2 | +17,820 | 3 | Design fetch + PRD comparison setup |
| 105 | +11,707 | 48 | Continued tab edits |

**Best turn for compaction proof:** **turn 100** (58 tools, mid-session cumulative naive ~516K tokens).

---

## File re-reads (ledger targets)

| File | Reads | Synthesizer fix |
|------|------:|-----------------|
| `SettingsTab.jsx` | 33 | Keep latest snippet only |
| `index.html` | 24 | Same |
| `BrandingTab.jsx` | 21 | Same (whitelabel work turns 88–120) |
| `data.js` | 12 | Mock data — single canonical version in ledger |
| `OrgDetail.jsx` | 12 | Tab shell — dedupe reads |

Same failure mode as meet-chavda (`Admin.tsx` 21×): iterative UI work re-injects file bodies into history.

---

## Tool mix

| Tool | Share | Dreaming v4 rule |
|------|------:|----------------|
| Edit | 50.7% | Latest edit per file in ledger |
| Bash | 21.4% | Collapse `sed`/loop output |
| Read | 19.0% | Dedupe by path |
| TaskCreate / TaskUpdate | 6.9% | Summarize task list in ledger |

Om is **Edit-dominant** (UI prototype) vs meet-chavda’s **Bash-dominant** CMDB research session.

---

## Native caching

| Signal | Om | meet-chavda (compare) |
|--------|-----|------------------------|
| Assistant msgs with cache_read | **99.9%** | 99.2% |
| User turns with cache_read | **94.2%** | 89.8% |
| Turns with no cache signal | **5.8%** | 9.8% |

Turns 3–7 show **no cache** (early session churn before turn-8 spike). After turn 8, cache_read climbs to 99%+ — same pattern as meet-chavda: caching works, but **history shape** still matters for counterfactual payload size and cache-write events on growth.

---

## Compaction proof (offline `compare_compaction.py`)

| Turn | Naive (cumul.) | Preprocessed window | Synthesizer-shaped | vs naive |
|------|---------------:|--------------------:|-------------------:|---------:|
| 8 | 108,984 | 992 | 1,144 | **98.9%** |
| 63 | 349,003 | 2,179 | 2,569 | **99.3%** |
| **100** | **516,436** | **2,365** | **2,748** | **99.5%** |
| 120 | 648,761 | 2,703 | 3,083 | **99.5%** |

Exports: `stats/om_compare_turn{8,63,100,120}.json`

**Interpretation:** Even at turn 8 (only 8 user turns in), naive context is already ~109K tokens because of 68 tool calls in one turn. Dreaming v4 preprocessing alone drops the 10-turn window to **~1K tokens**. By turn 100, naive cumulative is **half a million tokens**; synthesizer-shaped payload stays **~2.7K**.

Optional Haiku ledger replay:

```bash
.venv/bin/python context-synthesizer/compare_compaction.py \
  --cli-root context-synthesizer/stats/backups/om/.claude/projects \
  --session dcb92020 --turn 100 --run-dreaming --haiku
```

---

## Native `/compact` vs synthesizer

| | Claude Code native | Synthesizer (Dreaming v4) |
|--|-------------------|---------------------------|
| Compactions in session | **1** | Would fire **12×** (@ 10-turn threshold) |
| Trigger | User or near context limit | Proactive on turn count + spike rules |
| Goal | Fit in window | Bounded ledger + last-10 turns |

On a 120-turn UI sprint, native compact ran **once** while history counterfactual grew to **~649K tokens** by turn 120.

---

## How the synthesizer helps Om specifically

1. **Turn-8 burst** — 68 tools in one user turn (mass PRD fixes). Without compaction, a single turn can add ~53K tokens; preprocessing collapses the sliding window to **<1K**.
2. **Tab iteration** — 33× `SettingsTab.jsx` reads. Ledger holds one latest state instead of replaying edits in history.
3. **Whitelabel / branding arc** (turns 88–120) — `BrandingTab.jsx` re-read 21×; synthesizer keeps portal/URL decisions in ledger, not full file bodies.
4. **Long session without marathon length** — 120 turns proves value **before** 200+ turn territory; good pilot profile for proxy rollout.

---

## Reproduce

```bash
cd ~/Out-of-bound-chronicles/context-synthesizer

../.venv/bin/python analyze_hot_session.py \
  --source claude --cli-root stats/backups/om/.claude/projects \
  --session dcb92020 --export stats/om_hot_dcb92020.json

../.venv/bin/python analyze_claude_caching.py \
  --cli-root stats/backups/om/.claude/projects

../.venv/bin/python compare_compaction.py \
  --cli-root stats/backups/om/.claude/projects \
  --session dcb92020 --turn 100
```

---

## See also

- [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md) — meet-chavda vs chandresh vs Om
- [MEET_CHAVDA_CORPUS_REPORT.md](MEET_CHAVDA_CORPUS_REPORT.md) — meet-chavda reference corpus
- [COMPACTION_PROOF_REPORT.md](COMPACTION_PROOF_REPORT.md) — meet-chavda turn 178 deep dive
- [CHANDRESH_CORPUS_REPORT.md](CHANDRESH_CORPUS_REPORT.md) — chandresh zip corpus
