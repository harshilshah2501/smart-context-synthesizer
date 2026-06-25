# Context Synthesizer

Local proxy + compaction layer for **Claude Code** and **Cursor**.

**All documentation:** [../docs/README.md](../docs/README.md) · [../docs/guides/DOCS_CHEATSHEET.md](../docs/guides/DOCS_CHEATSHEET.md)

| Doc | Read when |
|-----|-----------|
| [../docs/guides/DEVELOPER_ONBOARDING.md](../docs/guides/DEVELOPER_ONBOARDING.md) | **Install & setup** |
| [../docs/guides/CSYNTH_QUICK_REFERENCE.md](../docs/guides/CSYNTH_QUICK_REFERENCE.md) | **`csynth` CLI** |
| [../docs/guides/COST_SAVINGS.md](../docs/guides/COST_SAVINGS.md) | Cost vs payload on dashboard |
| [../docs/guides/DASHBOARD.md](../docs/guides/DASHBOARD.md) | Live metrics UI |
| [../docs/guides/CURSOR_TEST.md](../docs/guides/CURSOR_TEST.md) | Cursor OpenAI shim (partial tool parity) |
| [../docs/context_os_technical_report.md](../docs/context_os_technical_report.md) | Gateway design |

---

## Install

**From git:**

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh your.handle
```

**From release tarball:**

```bash
tar -xzf context-synthesizer-toolkit-0.1.1.tar.gz
cd context-synthesizer-toolkit-0.1.1
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
csynth upgrade    # in-place update from GitHub
```

**Reinstall** (wipes install dir): `bash install.sh your.handle --reinstall`

**Upgrade bootstrap** (if `csynth upgrade` unknown): `bash scripts/upgrade.sh`

---

## Code layout

| Path | Purpose |
|------|----------|
| `proxy_message_bridge.py` | Tool-faithful message assembly (`/v1/messages`) |
| `proxy_tool.py` | Gateway + dashboard |
| `compaction.py` | Dreaming v4 summarization |
| `ledger_validation.py` | L2 post-compaction validation |
| `dashboard_api.py` | Dashboard aggregation |
| `telemetry.py` | Cost / cache bifurcation math |
| `scripts/csynth` | Post-install CLI |
| `scripts/upgrade.sh` | In-place upgrade |
| `experimental/` | Unsupported archives (not loaded by proxy) |
| `stats/` | **Local only** — gitignored |
