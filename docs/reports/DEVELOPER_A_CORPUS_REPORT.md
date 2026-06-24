# Developer A Corpus Report — CMDB research sessions

> **Anonymized corpus:** Developer handles (developer-a/b/c) replace real identities from a private study. Session IDs and aggregate metrics are preserved; no raw exports are in this repository.


**Date:** 2026-06-12  
**Source:** `claude-folder-backup.zip` → `stats/backups/developer-a/.claude/projects/`  
**Developer:** developer-a  
**Primary project:** `cmdb-research-repository` (CMDB pipeline + React frontend)

---

## Executive summary

developer-a is the **reference corpus** — 32 sessions, 859 user turns, including the longest session studied so far (**415 turns**, `ac4ecef7`).

| | developer-a | developer-b | developer-c |
|--|-------------|-----------|-----|
| Sessions | **32** | 99 | 1 |
| Longest session | **415 turns** | 28 turns | 120 turns |
| Session compression est. (hot) | **97.5%** | 68.9% | 90.9% |
| Turn-level cache_read | **~90%** | ~47% | 94.2% |
| Tool profile | **Bash + Edit** | Read + Java | Edit-heavy UI |
| Best turn-level proof | turn 178: **99.5%** | turn 23: 95.2% | turn 100: 99.5% |

**Plain English:** This developer ran marathon CMDB research sessions with heavy Bash pipelines, screenshot reads, and file re-reads. Claude caches ~99% of input, but a full transcript counterfactual reaches **~926K tokens** vs **~23K** synthesizer-shaped. At turn 178 (PNG screenshot spike), savings hit **99.5%**.

**Turn-178 deep dive (Haiku ledger):** [COMPACTION_PROOF_REPORT.md](COMPACTION_PROOF_REPORT.md)

---

## Import

```bash
bash context-synthesizer/scripts/import_claude_backup.sh \
  path/to/claude-folder-backup.zip \
  --developer developer-a
```

Or from an existing backup tree:

```bash
cd context-synthesizer
../.venv/bin/python import_claude_sessions.py \
  --cli-root stats/backups/developer-a/.claude/projects \
  --developer developer-a --min-turns 25 \
  --output stats/developer-a_corpus.jsonl \
  --export stats/developer-a_corpus.csv
```

**Outputs:**

| File | Description |
|------|-------------|
| `stats/backups/developer-a/.claude/projects/` | Extracted transcripts |
| `stats/developer-a_corpus.jsonl` | Mode D corpus (32 sessions) |
| `stats/developer-a_corpus.csv` | CSV summary |
| `stats/developer-a_hot_ac4ecef7.json` | Hot session deep dive |

---

## Corpus overview

| Metric | Value |
|--------|------:|
| Sessions imported | 32 |
| Total user turns | 859 |
| Assistant API messages | 8,173 |
| Sessions with token `usage` | 27 / 32 |
| Models | `claude-opus-4-7`, `claude-opus-4-8`, `<synthetic>` |

### Top sessions by synthesizer savings potential

| Session | Turns | Real tokens | Synth est. | Save % | Tools | Cache % |
|---------|------:|------------:|-----------:|-------:|------:|--------:|
| **ac4ecef7** | **415** | 542,858 | 22,850 | **97.5%** | 1,722 | 99.3% |
| 4e961ee7 | 89 | 504,347 | 25,044 | 87.0% | 628 | 51.4% |
| f0b1556a | 84 | — | 1,849 | 99.2% | 620 | 0.0% |
| 64518332 | 48 | 98,645 | 8,040 | 74.2% | 9 | 96.7% |
| 9fd659d0 | 45 | 567,501 | 810,346 | 31.0% | 382 | 99.2% |

Short sessions often show low or negative save % — synthesizer overhead (ledger + window) exceeds naive history when sessions are brief. **Value concentrates in long, tool-heavy sessions.**

---

## Hot session: `ac4ecef7` (415 turns)

| Metric | Value |
|--------|------:|
| User turns | 415 |
| Assistant messages | 3,410 |
| Tool calls | 1,722 |
| Unique files | 234 |
| Real input tokens (last turn) | 541,343 |
| Cache read | 537,417 (**99.3%**) |
| Output tokens | 716,416 |
| Naive est. → Synth est. | 926,162 → 22,850 tokens (**97.5%**) |
| Native auto-compact | **3×** |
| Synthesizer triggers @ turn 10 | **~41×** |

**Task shape:** CMDB research — pipeline orchestration, ServiceNow integration, React admin UI, relationship graphs, printer identification via screenshots.

### Context growth

```
naive: ▁▁▁▁▁▁▁▁▁▁▁▁▂▂▂▃▃▃▃▃▃▄▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▇▇▇▇▇█
synth: ▁▂▁▁▁▁▁▁▂▁▁▃▁▃▁▄▂▃▁▁▁█▃▃▁▂▂▂▅▁▁▁▁▁▁▁▁▁▁▁▁▁▁▅▃▁▁▁
```

### Top growth spikes

| Turn | Δ tokens (est.) | Tools | What happened |
|------|----------------:|------:|---------------|
| **178** | +123,713 | 40 | PNG screenshot reads — base64 image bloat (printer UI) |
| 235 | +66,586 | 20 | Continued pipeline / metadata work |
| 372 | +40,266 | 3 | Large assistant payload |
| 94 | +38,323 | 55 | Tool-heavy mid-session burst |

### Top file re-reads

| File | Reads | Synthesizer fix |
|------|------:|-----------------|
| `Admin.tsx` | 21 | Ledger: latest component state |
| `a4_identification.py` | 14 | Latest pipeline agent snippet |
| `RelationshipGraph.tsx` | 10 | Dedupe graph component reads |
| `orchestrator.py` | 10 | Single canonical orchestrator state |

### Tool mix

| Tool | Share | Dreaming v4 rule |
|------|------:|----------------|
| Bash | 39.7% | Collapse pipeline / docker output |
| Edit | 33.5% | Latest edit per file |
| Read | 16.3% | Dedupe by path (especially images) |

---

## Native caching

| Signal | developer-a (32 sessions) | Hot session `ac4ecef7` |
|--------|--------------------------:|-----------------------:|
| Assistant msgs with cache_read | **99.2%** | 99.3% |
| User turns with cache_read | **89.8%** | ~99%+ after warm-up |
| Turns with no cache signal | 9.8% | rare after turn 10 |

**Interpretation:** Claude Code already caches brilliantly. The synthesizer is **not** about enabling caching — it shrinks what gets cached and keeps the recent window clean.

---

## Compaction proof (offline `compare_compaction.py`)

### Turn 178 — worst spike

| Payload | ~Tokens | vs naive |
|---------|--------:|---------:|
| Naive (turns 1–178) | 724,562 | — |
| Preprocessed 10-turn window | 2,543 | 98.4% vs raw window |
| Synthesizer-shaped | 2,912 | **99.6%** |

Export: `stats/developer-a_compare_turn178.json`

### Turn 178 with Haiku ledger (optional)

```bash
.venv/bin/python context-synthesizer/compare_compaction.py \
  --cli-root context-synthesizer/stats/backups/developer-a/.claude/projects \
  --session ac4ecef7 --turn 178 --run-dreaming --haiku
```

Full narrative + Haiku ledger quality review: [COMPACTION_PROOF_REPORT.md](COMPACTION_PROOF_REPORT.md)

---

## Native `/compact` vs synthesizer

| | Claude Code native | Synthesizer (Dreaming v4) |
|--|-------------------|---------------------------|
| Compactions in `ac4ecef7` | **3** | Would fire **~41×** |
| Trigger | User `/compact` or near limit | Proactive every 10 turns + spike rules |
| Final real input prefix | **541K tokens** | Shaped counterfactual **~23K** |

Native compact did **not** prevent prefix bloat over 415 turns.

---

## How the synthesizer helps developer-a specifically

1. **Marathon sessions** — steady naive growth over 400+ turns; compaction every ~10 turns is essential.  
2. **Bash pipeline logs** — docker, migrations, orchestrator output collapsed in preprocessing.  
3. **Screenshot / image reads** — turn 178 dumps base64 PNG data; ledger + window strip low-value blobs.  
4. **File re-read loops** — `Admin.tsx` 21×; ledger holds one latest state.  
5. **Phase 2 regression baseline** — `developer-a_corpus.jsonl` is the drift-check reference for importer changes.

---

## Reproduce

```bash
cd ~/Out-of-bound-chronicles/context-synthesizer

../.venv/bin/python analyze_hot_session.py \
  --source claude --cli-root stats/backups/developer-a/.claude/projects \
  --session ac4ecef7 --export stats/developer-a_hot_ac4ecef7.json

../.venv/bin/python analyze_claude_caching.py \
  --cli-root stats/backups/developer-a/.claude/projects

../.venv/bin/python compare_compaction.py \
  --cli-root stats/backups/developer-a/.claude/projects \
  --session ac4ecef7 --turn 178
```

---

## See also

- [COMPACTION_PROOF_REPORT.md](COMPACTION_PROOF_REPORT.md) — turn 178 proof in plain English (+ Haiku ledger)
- [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md) — developer-a vs developer-b vs developer-c
- [DEVELOPER_B_CORPUS_REPORT.md](DEVELOPER_B_CORPUS_REPORT.md) · [DEVELOPER_C_CORPUS_REPORT.md](DEVELOPER_C_CORPUS_REPORT.md)
- [SYNTHESIZER_RND_REPORT.md §7](SYNTHESIZER_RND_REPORT.md#7-developer-corpus-developer-a) — extended R&D notes
