# Deploying the Context Synthesizer

**Developers never clone git.** They run **`run-setup.sh` once** (~5 min) from the SharePoint package. After that: **live compaction proxy** (primary) + optional weekly SharePoint uploads.

| Role | After setup |
|------|-------------|
| **Developer** | Use Claude Code normally (proxy runs in background); 0 min/week for cron |
| **Team lead** | Pull drive → `team_rollup.sh` (~1 min/week) |

**Send developers:** [TEAM_ANNOUNCEMENT.md](TEAM_ANNOUNCEMENT.md) (copy-paste) · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [DASHBOARD.md](DASHBOARD.md) (live metrics)

> **Motadata teams:** use only the section below. Skip [Alternative: GitHub / rclone](#alternative-github--rclone).

---

## Motadata / SharePoint — share the package directly

> **Repo is private** — do not use `curl` from GitHub.  
> **Share one installer package** on SharePoint; developers run **`run-setup.sh`**.

### Team lead — build & share once

```bash
cd /path/to/Out-of-bound-chronicles
bash context-synthesizer/packaging/build-release-tarball.sh
```

Upload **one** of these to SharePoint (`ContextSynthesizer/`):

| Share | What |
|-------|------|
| **Recommended** | Extracted folder `context-synthesizer-toolkit-YYYY.MM.DD/` from `packaging/build/` |
| Or | Single file `context-synthesizer-toolkit-YYYY.MM.DD.tar.gz` (devs extract after sync) |

**Configure once** in the package (before or after upload):

```bash
# Edit team.conf inside the package folder:
SYNC_DIR="$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
ENABLE_PROXY=1          # live compaction (default)
ENABLE_WEEKLY_CRON=1    # optional Monday SharePoint upload (default)
```

Share the SharePoint link → team clicks **Sync** in OneDrive.

### Developer — one command

Open terminal in the synced package folder:

```bash
bash run-setup.sh harshil.shah
```

Use Azure email local-part (`firstname.lastname`). No git or rclone.

See `INSTALL.txt` inside the package. **Live compaction is on by default** (`ENABLE_PROXY=1` in `team.conf`). Claude Code Max/Pro login forwards auth — no per-developer API key at setup.

**Live dashboard:** after setup, run `bash context-synthesizer/scripts/open_dashboard.sh`. On **WSL**, open the **WSL IP** URL in Windows browser (not `127.0.0.1`). See [DASHBOARD.md](DASHBOARD.md).

Weekly files (optional) are **copied** into the synced folder; OneDrive uploads to SharePoint.

**Team lead rollup** (same synced folder on your machine):

```bash
bash context-synthesizer/scripts/pull_from_drive.sh \
  "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
bash context-synthesizer/scripts/team_rollup.sh
```

Optional team-lead cron (Mondays 09:15, adjust path to your synced toolkit):

```cron
15 9 * * 1 bash /path/to/context-synthesizer-toolkit-YYYY.MM.DD/context-synthesizer/scripts/pull_from_drive.sh "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly" && bash /path/to/context-synthesizer-toolkit-YYYY.MM.DD/context-synthesizer/scripts/team_rollup.sh
```

---

## Architecture

```text
run-setup.sh / install.sh  →  toolkit folder (SharePoint sync, in-place)
                                        │
Claude Code ──► proxy (default ON) ─────┼── /dashboard  (live bifurcation UI)
~/.claude/projects/ ────────────────────┼── weekly_sync.sh (cron, optional)
                                        ▼
                              OneDrive sync folder (SharePoint)
                                        │
                              pull_from_drive.sh → team_rollup.sh
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Setup fails at proxy step | Enable systemd (WSL: `[boot] systemd=true` in `/etc/wsl.conf`, then `wsl --shutdown`) |
| Download fails | Use tarball from SharePoint; extract and run `run-setup.sh` from package folder |
| No Monday upload | Check `~/.local/state/context-synthesizer/weekly-*.log`; verify `SYNC_DIR` in `team.conf` |
| Proxy `activating (auto-restart)` / exit 1 | See below |
| Proxy down | `systemctl --user restart context-synthesizer-proxy` |
| Reinstall | `bash install.sh --reinstall --developer ...` from package root |

### Proxy won't start (exit-code / auto-restart)

```bash
# 1. See the real error (systemd often hides it in status alone)
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager

# 2. Or run in the foreground
cd /path/to/toolkit
.venv/bin/python context-synthesizer/proxy_tool.py
```

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: uvicorn` (or `fastapi`) | `bash context-synthesizer/scripts/setup.sh` |
| `address already in use` / port 8080 | Often **Tabby** or another IDE plugin (`ss -tlnp \| grep 8080`). Set `PROXY_PORT=8081` in `context-synthesizer/.env`, then re-run `configure_claude_proxy.sh` and `install_proxy_service.sh` |
| `Claude.md not found` | Re-extract toolkit; file must exist at `context-synthesizer/Claude.md` |

Preflight helper: `bash context-synthesizer/scripts/check_proxy_ready.sh`

**Dashboard (WSL):** `bash context-synthesizer/scripts/open_dashboard.sh` — do not use `127.0.0.1` in Windows browser. See [DASHBOARD.md](DASHBOARD.md).

---

## Script reference

| Script | Who |
|--------|-----|
| `run-setup.sh` (package root) | **Developer entry point** (Motadata) |
| `install.sh` (package root) | Called by `run-setup.sh`; also direct install |
| `packaging/build-release-tarball.sh` | Team lead — build SharePoint bundle |
| `scripts/setup_developer.sh` | Called by install.sh |
| `scripts/check_proxy_ready.sh` | Preflight before proxy install |
| `scripts/open_dashboard.sh` | Print/open dashboard URL (WSL-aware) |
| `scripts/weekly_sync.sh` | Cron |
| `static/dashboard.html` + `/dashboard` | Live bifurcation UI (same port as proxy) |
| `scripts/pull_from_drive.sh` | Team lead |

More: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [CORPUS_COMPARATIVE_ANALYSIS.md](../reports/CORPUS_COMPARATIVE_ANALYSIS.md)

---

## Backup zip import (team lead)

```bash
bash context-synthesizer/scripts/import_claude_backup.sh backup.zip --developer meet-chavda
```

---

## Alternative: GitHub / rclone

> **Not for Motadata rollout.** Use SharePoint + `run-setup.sh` above. This section is for public-repo or Google Drive deployments.

### Publish installer (once)

**Path A — GitHub raw (public repo only):**

```text
https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh
```

**Path B — shared drive tarball:**

```bash
bash context-synthesizer/packaging/build-release-tarball.sh
# Upload context-synthesizer-toolkit-YYYY.MM.DD.tar.gz + install.sh to shared drive
```

### Developer install (rclone)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer THEIR_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

Or from a synced drive tarball:

```bash
bash /path/from/drive/install.sh \
  --tarball-file /path/from/drive/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz \
  --developer THEIR_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

| Flag / `team.conf` | Effect |
|--------------------|--------|
| `ENABLE_PROXY=1` / `--enable-proxy` | Live compaction during Claude Code sessions (**default** in `run-setup.sh`) |
| `ENABLE_WEEKLY_CRON=1` / `--install-cron` | Monday auto-export + upload (**default** in `run-setup.sh`) |
| `--sync-dir` / `SYNC_DIR` | OneDrive folder for weekly upload (SharePoint teams) |
| `--rclone-remote` | Shared drive destination (optional) |

### rclone setup (team lead, once)

1. Create `ContextSynthesizer/weekly/` on Google Drive (or S3).  
2. `rclone config` → remote name e.g. `gdrive`.  
3. Give developers the remote path: `gdrive:Shared/ContextSynthesizer/weekly`  
4. Each developer configures the **same remote name** on their machine (`rclone config` once).

### Team lead weekly rollup (rclone)

```bash
bash context-synthesizer/scripts/pull_from_drive.sh \
  'gdrive:Shared/ContextSynthesizer/weekly'

bash context-synthesizer/scripts/team_rollup.sh
```

Optional cron (Mondays 09:15):

```cron
15 9 * * 1 bash $HOME/.local/share/context-synthesizer/context-synthesizer/scripts/pull_from_drive.sh 'gdrive:Shared/ContextSynthesizer/weekly' && bash $HOME/.local/share/context-synthesizer/context-synthesizer/scripts/team_rollup.sh
```
