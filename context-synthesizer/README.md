# Context Synthesizer

Offline analysis and tuning toolkit for **smart context compaction**.

`proxy_tool.py` is the **gateway implementation target**; the team workflow is **offline** corpus import (Modes A / C / D).

**All documentation:** [../docs/README.md](../docs/README.md)

| Doc | Read when |
|-----|-----------|
| [../docs/guides/Usage.md](../docs/guides/Usage.md) | Per-mode setup (A / C / D) |
| [../docs/guides/DEVELOPER_ONBOARDING.md](../docs/guides/DEVELOPER_ONBOARDING.md) | **Start here** — one-time setup |
| [../docs/guides/DEPLOY.md](../docs/guides/DEPLOY.md) | Team lead — drive + rollup |
| [../docs/guides/DASHBOARD.md](../docs/guides/DASHBOARD.md) | **Live dashboard** — bifurcation & savings |
| [../docs/reports/SYNTHESIZER_RND_REPORT.md](../docs/reports/SYNTHESIZER_RND_REPORT.md) | R&D record, roadmap |
| [../docs/reports/MEET_CHAVDA_CORPUS_REPORT.md](../docs/reports/MEET_CHAVDA_CORPUS_REPORT.md) | meet-chavda corpus (reference) |
| [../docs/reports/COMPACTION_PROOF_REPORT.md](../docs/reports/COMPACTION_PROOF_REPORT.md) | Turn-178 deep dive |
| [../docs/reports/CHANDRESH_CORPUS_REPORT.md](../docs/reports/CHANDRESH_CORPUS_REPORT.md) | chandresh corpus test |
| [../docs/reports/OM_CORPUS_REPORT.md](../docs/reports/OM_CORPUS_REPORT.md) | om Org Mgmt session |
| [../docs/reports/CORPUS_COMPARATIVE_ANALYSIS.md](../docs/reports/CORPUS_COMPARATIVE_ANALYSIS.md) | Three-developer comparison |
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

## Quick start (developers)

**Motadata / SharePoint package:** `bash run-setup.sh firstname.lastname` — **live compaction on by default** (`ENABLE_PROXY=1` in `team.conf`).

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

Installs to `~/.local/share/context-synthesizer` — no git clone. Proxy uses Claude Code session auth (Max/Pro); no separate API key at setup.

R&D / team lead: [../docs/guides/DEPLOY.md](../docs/guides/DEPLOY.md)

---

## Code layout

| Path | Purpose |
|------|---------|
| `import_*.py` | Mode A/C/D corpus import |
| `analyze_hot_session.py` | Single-session deep dive |
| `compare_compaction.py` | Naive vs Dreaming v4 at a spike turn |
| `collect_stats.py` | Team aggregate |
| `compaction.py` | Dreaming v4 rules |
| `proxy_tool.py` | Gateway + `/dashboard` live telemetry UI |
| `dashboard_api.py` / `dashboard_routes.py` | Dashboard aggregation + SSE |
| `static/dashboard.html` | Live bifurcation charts |
| `scripts/` | setup, weekly export, backup import |
| `stats/` | Local corpora (**gitignored**) |
| `packaging/` | Deprecated `.deb` legacy |
| `../docs/` | All guides and reports |
