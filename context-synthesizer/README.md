# Context Synthesizer

Offline analysis and tuning toolkit for **smart context compaction** — study long IDE sessions, estimate synthesizer-shaped payloads, and tune Dreaming rules. Built from real Claude Code and Cursor session logs.

The repo also contains `proxy_tool.py` (four-layer gateway + Dreaming) as the **implementation target** the synthesizer optimizes toward. The team does **not** route live traffic through it.

**Docs:**

| Doc | Read when |
|-----|-----------|
| **[Usage.md](Usage.md)** | Per-mode setup ([A / C / D](#data-collection-modes)) |
| **[SYNTHESIZER_RND_REPORT.md](SYNTHESIZER_RND_REPORT.md)** | Corpus analysis, caching findings, roadmap |
| **[PHASE_2_REPORT.md](PHASE_2_REPORT.md)** | Phase 2 validation results (pass/fail vs criteria) |
| **[DEPLOY.md](DEPLOY.md)** | Phase 3 rollout — setup, weekly export, team rollup |
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

# Phase 2 regression suite (Modes D + C on dev backup)
.venv/bin/python context-synthesizer/run_phase2_validation.py

# Phase 3 weekly export (developers)
bash context-synthesizer/scripts/export_weekly_corpus.sh --mode d
```

Full rollout: **[DEPLOY.md](DEPLOY.md)**

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
| Hot session + caching analyzers | |
| `run_phase2_validation.py` + `PHASE_2_REPORT.md` | |
| `scripts/*.sh` + `DEPLOY.md` | Phase 3 weekly corpus deploy |
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
| `run_phase2_validation.py` | D/C | Repeatable Phase 2 corpus regression suite |
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
