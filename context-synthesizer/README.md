# Context Synthesizer

Local proxy + compaction layer for **Claude Code** and **Cursor**.

**All documentation:** [../docs/README.md](../docs/README.md) · [../docs/guides/DOCS_CHEATSHEET.md](../docs/guides/DOCS_CHEATSHEET.md)

| Doc | Read when |
|-----|-----------|
| [../docs/guides/DEVELOPER_ONBOARDING.md](../docs/guides/DEVELOPER_ONBOARDING.md) | **Install & setup** |
| [../docs/guides/CSYNTH_QUICK_REFERENCE.md](../docs/guides/CSYNTH_QUICK_REFERENCE.md) | **`csynth` CLI** |
| [../docs/guides/COST_SAVINGS.md](../docs/guides/COST_SAVINGS.md) | Cost vs payload on dashboard |
| [../docs/guides/DASHBOARD.md](../docs/guides/DASHBOARD.md) | Live metrics UI |
| [../docs/guides/DEPLOY.md](../docs/guides/DEPLOY.md) | Build tarball / team publish |
| [../docs/context_os_technical_report.md](../docs/context_os_technical_report.md) | Gateway design |

---

## Install

**From git checkout:**

```bash
cd context-synthesizer
bash install.sh your.handle
```

**From toolkit tarball:**

```bash
cd context-synthesizer-toolkit-latest
bash run-setup.sh your.handle
```

```bash
csynth doctor && csynth dashboard
```

Proxy on by default. Claude Max/Pro login — no API key at setup.

### `csynth`

```bash
csynth proxy on | off | restart
csynth status | doctor | dashboard | logs
```

Reinstall: `bash install.sh your.handle --reinstall`

---

## Offline analysis (no proxy)

| Mode | Tool |
|------|------|
| A — Claude Code logs | `import_cli_logs.py` |
| C — Cursor | `import_cursor_sessions.py` |
| D — Claude sessions | `import_claude_sessions.py` |

See [../docs/guides/Usage.md](../docs/guides/Usage.md).

---

## Team lead — build release

```bash
bash packaging/build-release-tarball.sh
```

Optional shared-drive publish (configure `packaging/share.conf` from `share.conf.example`):

```bash
cp packaging/share.conf.example packaging/share.conf
bash packaging/publish-to-sharepoint.sh
```

See [../docs/guides/DEPLOY.md](../docs/guides/DEPLOY.md).

---

## Code layout

| Path | Purpose |
|------|---------|
| `proxy_message_bridge.py` | Tool-faithful message assembly |
| `proxy_tool.py` | Gateway + dashboard |
| `compaction.py` | Dreaming v4 summarization |
| `telemetry.py` | Cost / cache bifurcation math |
| `scripts/csynth` | Post-install CLI |
| `stats/` | **Local only** — gitignored |
