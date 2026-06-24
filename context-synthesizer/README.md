# Context Synthesizer

Offline analysis and tuning toolkit for **smart context compaction**.

`proxy_tool.py` is the **gateway implementation target**; the team workflow is **offline** corpus import (Modes A / C / D) plus an optional **live proxy** for Claude Code (Max/Pro).

**All documentation:** [../docs/README.md](../docs/README.md)

| Doc | Read when |
|-----|-----------|
| [../docs/guides/DOCS_CHEATSHEET.md](../docs/guides/DOCS_CHEATSHEET.md) | **Cheatsheet** — doc map + commands by role |
| [../docs/guides/DEVELOPER_ONBOARDING.md](../docs/guides/DEVELOPER_ONBOARDING.md) | **Start here** — one-time setup |
| [../docs/guides/CSYNTH_QUICK_REFERENCE.md](../docs/guides/CSYNTH_QUICK_REFERENCE.md) | **`csynth` CLI** — install, proxy on/off, restart |
| [../docs/guides/COST_SAVINGS.md](../docs/guides/COST_SAVINGS.md) | **Why cost drops** when payload size looks flat |
| [../docs/guides/DASHBOARD.md](../docs/guides/DASHBOARD.md) | **Live dashboard** — bifurcation & savings |
| [../docs/guides/Usage.md](../docs/guides/Usage.md) | Per-mode setup (A / C / D) |
| [../docs/guides/DEPLOY.md](../docs/guides/DEPLOY.md) | Team lead — drive + rollup |
| [../docs/reports/SYNTHESIZER_RND_REPORT.md](../docs/reports/SYNTHESIZER_RND_REPORT.md) | R&D record, roadmap |
| [../docs/context_os_technical_report.md](../docs/context_os_technical_report.md) | Gateway design |

---

## Data collection modes

| Mode | Who | Tool |
|------|-----|------|
| **A** | Claude Code (default) | `import_cli_logs.py` |
| **C** | Cursor IDE | `import_cursor_sessions.py` |
| **D** | Claude Max / Pro | `import_claude_sessions.py` |

Modes A/C/D are **offline** — no API key, no proxy.

---

## Quick start (developers)

**Motadata / SharePoint:** download `context-synthesizer-toolkit-latest` from the synced folder, then:

```bash
cd context-synthesizer-toolkit-latest
bash run-setup.sh firstname.lastname
csynth doctor && csynth dashboard
```

Live compaction proxy is on by default (`ENABLE_PROXY=1`). Claude Max/Pro login only — no API key.

### `csynth` (after install)

```bash
csynth status          # proxy service + routing
csynth proxy on        # route through synthesizer
csynth proxy off       # direct Anthropic API
csynth restart         # restart proxy service
csynth dashboard       # live cost dashboard URL
csynth doctor          # full preflight
csynth logs            # tail proxy journal
```

**Reinstall:** `bash install.sh firstname.lastname --reinstall`

See [../docs/guides/CSYNTH_QUICK_REFERENCE.md](../docs/guides/CSYNTH_QUICK_REFERENCE.md).

**Team lead — publish a release** (from dev machine with OneDrive sync):

```bash
cd context-synthesizer
bash packaging/publish-to-sharepoint.sh
```

Builds the toolkit and copies to `OneDrive - Motadata/Context-Synthesizer/`. See [../docs/guides/DEPLOY.md](../docs/guides/DEPLOY.md).

---

## Code layout

| Path | Purpose |
|------|---------|
| `proxy_message_bridge.py` | Tool-faithful message assembly + API passthrough |
| `proxy_tool.py` | Gateway + `/dashboard` live telemetry UI |
| `import_*.py` | Mode A/C/D corpus import |
| `compaction.py` | Dreaming v4 rules |
| `dashboard_api.py` / `dashboard_routes.py` | Dashboard aggregation + SSE |
| `static/dashboard.html` | Live bifurcation charts |
| `scripts/csynth` | Post-install CLI |
| `packaging/` | SharePoint publish, tarball build |
| `stats/` | Local corpora (**gitignored**) |
| `../docs/` | All guides and reports |
