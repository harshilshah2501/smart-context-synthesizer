# Corpus Comparative Analysis — Three Developers

**Date:** 2026-06-12  
**Corpora:** meet-chavda · chandresh · om  
**Question:** Where does the context synthesizer help, and how much — across different developer session shapes?

---

## Executive summary

| Developer | Corpus shape | Longest session | Session compression | Best turn proof | Primary waste pattern |
|-----------|----------------|----------------:|--------------------:|----------------:|------------------------|
| **meet-chavda** | 32 sessions, CMDB research | **415** turns | **97.5%** | turn 178: **99.5%** | Bash logs + PNG screenshots |
| **chandresh** | 99 sessions, Java/NR | **28** turns | **68.9%** | turn 23: **95.2%** | Java file re-reads + tool spikes |
| **om** | 1 session, React Org Mgmt UI | **120** turns | **90.9%** | turn 100: **99.5%** | Edit loops + tab file re-reads |

**Unified conclusion:** The synthesizer is a **history architect**, not a caching enabler. All three corpora show **high native cache_read** on long sessions (94–99%), yet counterfactual naive transcripts still grow to **100K–900K+ tokens**. Dreaming v4 + four-layer payload keeps shaped context in the **~2K–32K** range at spike turns.

**Who benefits most (live proxy pilot order):**

1. **meet-chavda** — extreme length, proven 415-turn session  
2. **om** — 120-turn UI sprint, 99.5% at turn 100, Edit-heavy  
3. **chandresh** — valuable on longest Java sessions; corpus is mostly short tasks

---

## Corpus at a glance

| Metric | meet-chavda | chandresh | om |
|--------|------------:|----------:|---:|
| Sessions | 32 | 99 | 1 |
| Total user turns | 859 | 637 | 120 |
| Sessions ≥100 turns | 1 | 0 | 1 |
| Sessions ≥25 turns | many | 2 | 1 |
| Hot session ID | `ac4ecef7` | `d326033e` | `dcb92020` |
| Hot session turns | 415 | 28 | 120 |
| Tool calls (hot) | 1,722 | 156 | 838 |
| Real input tokens (hot, last turn) | ~542K | ~87K | ~560K |
| Cache read % (hot) | 99.3% | 93.5% | 99.8% |
| Naive est. tokens (hot, final) | ~926K | ~100K | ~347K |
| Synth est. tokens (hot, final) | ~23K | ~31K | ~32K |
| Session compression est. | 97.5% | 68.9% | 90.9% |
| Native auto-compact (hot) | 3× | 1× | 1× |
| Synthesizer triggers (@10 turns) | ~41× | 2× | 12× |

---

## Session shape archetypes

```text
meet-chavda (ac4ecef7)     ████████████████████████████████████████  415 turns  marathon
om (dcb92020)              ████████████                              120 turns  sprint
chandresh (d326033e)       ███                                        28 turns  burst
```

| Archetype | Example | Synthesizer value driver |
|-----------|---------|--------------------------|
| **Marathon** | meet-chavda | Steady naive growth; compaction every ~10 turns essential |
| **Sprint** | om | Early mega-spike (turn 8, 68 tools) + sustained tab iteration |
| **Burst** | chandresh | Single-session spikes; lower session-level % on short corpora |

---

## Tool mix comparison (hot sessions)

| Tool | meet-chavda | chandresh (`d326033e`) | om |
|------|------------:|----------------------:|---:|
| Bash | **39.7%** | 17% | 21.4% |
| Edit | 33.5% | 18% | **50.7%** |
| Read | 16.3% | **40%** | 19.0% |
| Agent / Chrome MCP | — | — | (not dominant) |

**Dreaming v4 mapping:**

| Pattern | Rule | Strongest in |
|---------|------|--------------|
| Terminal / pipeline output | Bash collapse | meet-chavda |
| Repeated file reads | Read dedupe → ledger | chandresh, om |
| Iterative JSX/TS edits | Latest edit per file | om, meet-chavda |

---

## File re-read waste (top offender per corpus)

| Developer | Top re-read | Count | Synthesizer action |
|-----------|-------------|------:|--------------------|
| meet-chavda | `Admin.tsx` | 21× | Ledger: latest component state |
| chandresh | `SingleSignOnUtil.java` | 15× | Ledger: latest SSO util snippet |
| om | `SettingsTab.jsx` | 33× | Ledger: latest settings tab |

All three show the same underlying problem: **the IDE appends full file bodies on every Read/Edit cycle**. The ledger replaces N copies with one.

---

## Turn-level compaction proof (apples-to-apples)

Offline `compare_compaction.py` at each corpus’s worst spike turn:

| Developer | Session | Spike turn | Tools @ turn | Naive tokens | Synth-shaped | Reduction |
|-----------|---------|------------|-------------:|-------------:|-------------:|----------:|
| meet-chavda | `ac4ecef7` | 178 | 40 | ~725,000 | ~3,800 | **99.5%** |
| chandresh | `d326033e` | 23 | 40 | ~126,789 | ~6,098 | **95.2%** |
| om | `dcb92020` | 100 | 58 | ~516,436 | ~2,748 | **99.5%** |

**Insight:** Turn-level savings converge to **~95–99.5%** whenever a spike turn stacks dozens of tool results — regardless of whether the session is 28 or 415 turns total. Session-level compression % is lower on short corpora because overhead dominates early turns.

---

## Native caching vs synthesizer (all three)

| Signal | meet-chavda | chandresh | om |
|--------|------------:|----------:|---:|
| Assistant-level cache_read | 99.2% | 97.0% | 99.9% |
| Turn-level cache_read | ~90% | ~47% | 94.2% |
| “Caching fixes it” | **No** | **No** | **No** |

Claude Code already achieves excellent cache hit rates on long sessions. The synthesizer still matters because:

1. **Counterfactual naive history** (what would be sent without shaping) grows unbounded.  
2. **cache_write** on prefix growth is expensive even when reads are cheap.  
3. **Native `/compact`** fires 1–3× per session vs synthesizer’s **12–41×** proactive passes.  
4. **Model attention** — smaller shaped payload improves signal-to-noise even with cache.

---

## Native compact vs synthesizer triggers

| Developer | Hot turns | Native auto-compact | Synth @ turn 10 |
|-----------|----------:|--------------------:|----------------:|
| meet-chavda | 415 | 3 | ~41 |
| chandresh | 28 | 1 | 2 |
| om | 120 | 1 | 12 |

Native compaction is **reactive** (user `/compact` or near limit). Synthesizer is **proactive** — critical for om’s turn-8 burst before any auto-compact would fire.

---

## Recommendations by developer profile

### meet-chavda — marathon researcher

- **Pilot:** proxy on longest CMDB sessions first  
- **Tune:** Bash collapse + image/base64 dump stripping (turn 178 pattern)  
- **Metric:** turn 178 naive vs synth as regression gate  

### chandresh — many short Java tasks

- **Collect:** wait for or encourage longer sessions (25+ turns) for stronger session-level %  
- **Tune:** Read dedupe on utility classes (`*Util.java`)  
- **Metric:** turn 23 spike on `d326033e` as Java-session template  

### om — UI prototype sprint

- **Pilot:** strong candidate — 120 turns, 99.5% at turn 100, Opus 4.7  
- **Tune:** Edit-heavy ledger rules; `*Tab.jsx` dedupe  
- **Metric:** turn 8 (early 68-tool burst) + turn 100 (sustained sprint)  

---

## Team rollout implication

| Step | Action |
|------|--------|
| 1 | All three developers run weekly `export_weekly_corpus.sh --mode d` |
| 2 | Lead runs `team_rollup.sh` — compare compression distributions |
| 3 | Proxy pilots: **meet-chavda** + **om** first (long sessions) |
| 4 | Regression: `compare_compaction.py` on each corpus’s spike turn after `compaction.py` changes |

```bash
# Spike-turn regression suite (offline, no API key)
.venv/bin/python context-synthesizer/compare_compaction.py \
  --cli-root context-synthesizer/stats/backups/meet-chavda/.claude/projects \
  --session ac4ecef7 --turn 178

.venv/bin/python context-synthesizer/compare_compaction.py \
  --cli-root context-synthesizer/stats/backups/chandresh/projects \
  --session d326033e --turn 23

.venv/bin/python context-synthesizer/compare_compaction.py \
  --cli-root context-synthesizer/stats/backups/om/.claude/projects \
  --session dcb92020 --turn 100
```

---

## Source reports

| Developer | Detail report |
|-----------|---------------|
| meet-chavda | [MEET_CHAVDA_CORPUS_REPORT.md](MEET_CHAVDA_CORPUS_REPORT.md) · [COMPACTION_PROOF_REPORT.md](COMPACTION_PROOF_REPORT.md) (turn 178) |
| chandresh | [CHANDRESH_CORPUS_REPORT.md](CHANDRESH_CORPUS_REPORT.md) |
| om | [OM_CORPUS_REPORT.md](OM_CORPUS_REPORT.md) |

---

*Generated from Mode D imports and offline compaction replay on local session logs. Session data stays in `context-synthesizer/stats/` (gitignored).*
