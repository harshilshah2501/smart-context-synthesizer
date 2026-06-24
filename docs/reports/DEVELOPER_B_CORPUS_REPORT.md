# Chandresh Corpus Report — `claude-sessions.zip`

> **Anonymized corpus:** Developer handles (developer-a/b/c) replace real identities from a private study. Session IDs and aggregate metrics are preserved; no raw exports are in this repository.


**Date:** 2026-06-11  
**Source:** `context-synthesizer/claude-sessions.zip` (17 MB)  
**Developer:** developer-b  
**Project:** Java NR monitoring workspace (anonymized)

---

## Executive summary

The new corpus imported successfully (**99 sessions**). It is a **different shape** from developer-a:

| | developer-a | developer-b (this zip) |
|--|-------------|----------------------|
| Sessions | 32 | **99** |
| Longest session | **415** turns | **28** turns |
| Sessions ≥100 turns | 1 | **0** |
| Best compression (longest) | 97.5% | **68.9%** |
| p90 compression (all sessions) | 97.5% | **18.5%** |
| Turn-level cache_read | ~90% | **~47%** |

**Plain English:** This corpus has **more sessions but each one is shorter**. The synthesizer still helps on the longest Java/SSO session (~69% smaller), but we **cannot** apply the “≥90% on 100+ turn sessions” bar here — there are no 100+ turn sessions.

---

## Import

```bash
bash context-synthesizer/scripts/import_claude_backup.sh \
  context-synthesizer/claude-sessions.zip \
  --developer developer-b
```

**Note:** This zip uses `projects/` at the top level (not `.claude/projects/`). `import_claude_backup.sh` was updated to support that layout.

**Outputs:**

| File | Description |
|------|-------------|
| `stats/backups/developer-b/projects/` | Extracted transcripts |
| `stats/weekly/2026-06-11_developer-b_claude_backup.jsonl` | Mode D corpus |
| `stats/weekly/2026-06-11_developer-b_claude_backup.csv` | CSV summary |

---

## Corpus overview

| Metric | Value |
|--------|-------|
| Sessions imported | 99 |
| Total user turns | 637 |
| Sessions with token `usage` | 62 / 99 |
| Sessions ≥25 turns | 2 |
| Sessions ≥100 turns | 0 |

### Top sessions by turn count

| Session | Turns | Compression est. | Tools | Notes |
|---------|------:|-----------------|------:|-------|
| `d326033e` | 28 | **68.9%** | 156 | Longest — SSO / Java (`SingleSignOnUtil.java`) |
| `359a2170` | 25 | 76.4% | 242 | 2nd longest |
| `2ac32a0c` | 23 | 41.0% | 283 | Heavy tools, low save |
| `5065a563` | 22 | 74.4% | 50 | Good cache (99.7%) |

**25+ turn average compression:** 72.6% (0/2 pass ≥90%)

---

## Hot session: longest by turns (`d326033e`)

Best session to study for synthesizer value in this corpus.

| Metric | Value |
|--------|-------|
| User turns | 28 |
| Tool calls | 156 |
| Real input / cache read | 86,741 / 81,106 (**93.5%**) |
| Naive est. → Synth est. | 99,817 → 31,043 tokens (**68.9%**) |
| Native auto-compact | 1× |
| Synthesizer triggers @ turn 10 | Would fire at turns 10, 20 |

**Tool mix:** Read 40%, Edit 18%, Bash 17%, Agent 11%

**Top re-read:** `SingleSignOnUtil.java` — **15×** (ledger should keep latest only)

**Top spike:** Turn 17 (+14,344 tok), turn 23 (+13,132 tok, 40 tools)

**Recommendations from analyzer:**

- Token-based compaction on spikes (turns 17, 23)
- Dedupe `SingleSignOnUtil.java` reads
- Compare 1× native compact vs synthesizer’s 2+ triggers

Full JSON: `stats/developer-b_hot_d326033e.json`

---

## Hot session: largest file (`ed3f3007`)

`--largest` picks **biggest file**, not most turns. This session is only **6 turns** but **2.6 MB** of log — mostly **Chrome MCP** (`mcp__claude-in-chrome__computer` 79% of tools).

| Metric | Value |
|--------|-------|
| Turns | 6 |
| Compression est. | **-0.3%** (no win — almost all spike in one turn) |
| Spike | Turn 5: **+269,232 tokens** (browser automation) |

**Takeaway:** Short sessions with one huge tool dump are a **different failure mode** than developer-a’s long steady growth. Preprocessing + dump compaction at turn 5 would be the fix.

Full JSON: `stats/developer-b_hot.json`

---

## Native caching

| Signal | developer-b | developer-a (compare) |
|--------|-----------|------------------------|
| Assistant msgs with cache_read | **97.0%** | 99.2% |
| User turns with cache_read | **46.9%** | 89.8% |
| Turns with no cache signal | **52.0%** | 9.8% |

**Plain English:** Many sessions are **short or synthetic-model** runs with weak per-turn cache signals. Assistant-level caching is still high (97%), but turn-level warmth is **noisier** than developer-a.

Models seen: `claude-opus-4-6`, `claude-opus-4-7`, `claude-opus-4-8`, `claude-haiku-4-5`, `<synthetic>`

---

## Team rollup (`collect_stats.py`)

- **99 requests** (one row per session)
- Cache efficiency: **79.7%** of input tokens
- Estimated savings vs baseline: **55.6%**

---

## Verdict vs Phase 2 criteria

| Criterion | Target | developer-b result |
|-----------|--------|------------------|
| Compression ≥90% (100+ turns) | PASS | **N/A** — no 100+ turn sessions |
| Compression on longest session | — | **68.9%** (`d326033e`, 28 turns) |
| Corpus usable for tooling | — | **Yes** — import, hot session, caching, stats all work |
| Same playbook as developer-a | — | **Partial** — shorter sessions, Chrome MCP spikes |

---

## Suggested next steps

1. **Compaction proof on `d326033e` turn 23** (40-tool spike) — **done (offline)**:

   | Payload | ~Tokens |
   |---------|--------:|
   | Naive (turns 1–23) | 126,789 |
   | Raw 10-turn window | 61,905 |
   | Preprocessed window | 5,693 (**90.8%** smaller) |
   | Synthesizer-shaped | 6,098 (**95.2%** vs naive) |

   Export: `stats/developer-b_compare_turn23.json`

   Haiku ledger replay (optional):
   ```bash
   .venv/bin/python context-synthesizer/compare_compaction.py \
     --cli-root context-synthesizer/stats/backups/developer-b/projects \
     --session d326033e --turn 23 --run-dreaming --haiku
   ```

2. **Compaction proof on `ed3f3007` turn 5** (Chrome MCP spike):
   ```bash
   .venv/bin/python context-synthesizer/compare_compaction.py \
     --session ed3f3007 --turn 5 --cli-root context-synthesizer/stats/backups/developer-b/projects
   ```

3. **Wait for longer sessions** — this zip may be a snapshot of mostly short tasks; synthesizer wins grow with turn count.

4. Add `claude-sessions.zip` to `.gitignore` if not already (session data).

---

## Reproduce

```bash
cd ~/Out-of-bound-chronicles

bash context-synthesizer/scripts/import_claude_backup.sh \
  context-synthesizer/claude-sessions.zip --developer developer-b

.venv/bin/python context-synthesizer/analyze_hot_session.py \
  --cli-root context-synthesizer/stats/backups/developer-b/projects \
  --session d326033e --export context-synthesizer/stats/developer-b_hot_d326033e.json

.venv/bin/python context-synthesizer/analyze_claude_caching.py \
  --cli-root context-synthesizer/stats/backups/developer-b/projects

.venv/bin/python context-synthesizer/collect_stats.py \
  --logs context-synthesizer/stats/weekly/2026-06-11_developer-b_claude_backup.jsonl
```

---

## See also

- [CORPUS_COMPARATIVE_ANALYSIS.md](CORPUS_COMPARATIVE_ANALYSIS.md) — developer-a vs developer-b vs developer-c
- [DEVELOPER_C_CORPUS_REPORT.md](DEVELOPER_C_CORPUS_REPORT.md) — developer-c Org Mgmt session (120 turns)
- [DEVELOPER_A_CORPUS_REPORT.md](DEVELOPER_A_CORPUS_REPORT.md) — developer-a reference corpus
- [COMPACTION_PROOF_REPORT.md](COMPACTION_PROOF_REPORT.md) — developer-a turn 178 deep dive
