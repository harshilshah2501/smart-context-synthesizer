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

**Motadata / SharePoint:** download `context-synthesizer-toolkit-latest` from the synced folder, then:

```bash
cd context-synthesizer-toolkit-latest
bash run-setup.sh firstname.lastname
csynth doctor && csynth dashboard
```

Live compaction proxy is on by default (`ENABLE_PROXY=1`). Claude Max/Pro login only — no API key.

Toggle without reinstall:

```bash
csynth proxy off   # direct Anthropic API
csynth proxy on    # route through synthesizer again
```

**Team lead — publish a release** (from dev machine with OneDrive sync):

```bash
bash packaging/publish-to-sharepoint.sh
```

Copies to `OneDrive - Motadata/Context-Synthesizer/` — no `install.sh` edits per release.

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
| `scripts/open_dashboard.sh` | Print/open dashboard URL (WSL-aware) |
| `scripts/` | setup, weekly export, backup import |
| `stats/` | Local corpora (**gitignored**) |
| `packaging/` | Deprecated `.deb` legacy |
| `../docs/` | All guides and reports |
