# Context Synthesizer

Offline analysis and tuning toolkit for **smart context compaction** — study long IDE sessions, estimate synthesizer-shaped payloads, and tune Dreaming rules.

`proxy_tool.py` is the **gateway implementation target**; the team workflow is **offline** corpus import (Modes A / C / D).

**Full doc index:** [docs/README.md](docs/README.md)

| Doc | Read when |
|-----|-----------|
| [docs/guides/Usage.md](docs/guides/Usage.md) | Per-mode setup (A / C / D) |
| [docs/guides/DEPLOY.md](docs/guides/DEPLOY.md) | Team rollout, weekly export |
| [docs/reports/SYNTHESIZER_RND_REPORT.md](docs/reports/SYNTHESIZER_RND_REPORT.md) | R&D record, roadmap |
| [docs/reports/COMPACTION_PROOF_REPORT.md](docs/reports/COMPACTION_PROOF_REPORT.md) | Turn-178 proof (simple terms) |
| [docs/reports/CHANDRESH_CORPUS_REPORT.md](docs/reports/CHANDRESH_CORPUS_REPORT.md) | New corpus test |
| [../docs/context_os_technical_report.md](../docs/context_os_technical_report.md) | Gateway design |

---

## Data collection modes

| Mode | Who | Tool |
|------|-----|------|
| **A** | Claude Code (default) | `import_cli_logs.py` |
| **C** | Cursor IDE | `import_cursor_sessions.py` |
| **D** | Claude Max / Pro | `import_claude_sessions.py` |

All modes are **offline** — no API key, no proxy.

---

## Quick start

```bash
cd ~/Out-of-bound-chronicles
bash context-synthesizer/scripts/setup.sh

# Mode D — corpus import
.venv/bin/python context-synthesizer/import_claude_sessions.py \
  --developer "$(whoami)" --min-turns 25

# Hot session deep-dive
.venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --largest

# Compaction proof at a spike turn
.venv/bin/python context-synthesizer/compare_compaction.py \
  --session ac4ecef7 --turn 178

# Phase 2 regression
.venv/bin/python context-synthesizer/run_phase2_validation.py
```

Full rollout: [docs/guides/DEPLOY.md](docs/guides/DEPLOY.md)

---

## Code layout

| Path | Purpose |
|------|---------|
| `import_*.py` | Mode A/C/D corpus import |
| `analyze_hot_session.py` | Single-session deep dive |
| `analyze_claude_caching.py` | Native cache behavior |
| `compare_compaction.py` | Naive vs Dreaming v4 at a spike turn |
| `collect_stats.py` | Team aggregate |
| `run_phase2_validation.py` | Repeatable Phase 2 suite |
| `compaction.py` | Dreaming v4 rules |
| `proxy_tool.py` | Gateway (not team workflow) |
| `scripts/` | `setup.sh`, weekly export, backup import |
| `stats/` | Local corpora (**gitignored**) |
| `packaging/` | Deprecated `.deb` legacy |
| `docs/guides/` | How-to |
| `docs/reports/` | Analysis & proof reports |

---

## Shipped vs planned

| Shipped | Planned |
|---------|---------|
| Mode A/C/D pipeline | Production ~200K `Claude.md` |
| Dreaming v4 + `compare_compaction.py` | Live gateway pilot (BYOK) |
| Phase 2/3 scripts + reports | |
