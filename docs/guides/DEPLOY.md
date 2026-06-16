# Deploying the Context Synthesizer

**Developers never clone git.** They run **`install.sh` once** (~5 min). After that: **live compaction proxy** (primary) + optional weekly SharePoint uploads.

| Role | After setup |
|------|-------------|
| **Developer** | Use Claude Code normally (proxy runs in background); 0 min/week for cron |
| **Team lead** | Pull drive → `team_rollup.sh` (~1 min/week) |

**Send developers:** [TEAM_ANNOUNCEMENT.md](TEAM_ANNOUNCEMENT.md) (copy-paste) · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [DASHBOARD.md](DASHBOARD.md) (live metrics)

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

**Live dashboard:** after setup, open `http://127.0.0.1:<PROXY_PORT>/dashboard` (default `8080`, or `8081` if port conflict) — billing bifurcation, L1–L4 layers, naive vs shaped savings, compactions. Updates as you use Claude Code.

Weekly files (optional) are **copied** into the synced folder; OneDrive uploads to SharePoint.

**Team lead rollup** (same synced folder on your machine):

```bash
bash context-synthesizer/scripts/pull_from_drive.sh \
  "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
bash context-synthesizer/scripts/team_rollup.sh
```

---

## Architecture

```text
install.sh / run-setup.sh  →  toolkit folder (or ~/.local/share/context-synthesizer)
                                        │
Claude Code ──► proxy (default ON) ─────┼── /dashboard  (live bifurcation UI)
~/.claude/projects/ ────────────────────┼── weekly_sync.sh (cron, optional)
                                        ▼
                              OneDrive sync folder (SharePoint)
                                        │
                              pull_from_drive.sh → team_rollup.sh
```

---

## Step 0 — Team lead: publish installer (once)

### Path A — GitHub raw (public repo)

Developers use:

```text
https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh
```

Pin the link in Slack/wiki. Updates when you push to `main`.

### Path B — shared drive only (recommended for private teams)

Build a tarball from your machine:

```bash
cd /path/to/Out-of-bound-chronicles
bash context-synthesizer/packaging/build-release-tarball.sh
```

Upload to shared drive:

- `context-synthesizer-toolkit-YYYY.MM.DD.tar.gz`
- `install.sh` (copy from repo root)

Share the drive folder + rclone remote name with developers.

---

## Step 1 — Developer install (copy-paste to Slack)

**GitHub:**

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer THEIR_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

**Shared drive:**

```bash
bash /path/from/drive/install.sh \
  --tarball-file /path/from/drive/context-synthesizer-toolkit-2026.06.12.tar.gz \
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

---

## Step 2 — rclone (team lead, once)

1. Create `ContextSynthesizer/weekly/` on Google Drive (or S3).  
2. `rclone config` → remote name e.g. `gdrive`.  
3. Give developers the remote path: `gdrive:Shared/ContextSynthesizer/weekly`  
4. Each developer configures the **same remote name** on their machine (`rclone config` once).

---

## Step 3 — What developers see

### Live (default via `ENABLE_PROXY=1` / `--enable-proxy`)

Claude Code unchanged — synthesizer runs as `context-synthesizer-proxy` user service. Auth comes from your Claude Code session (Max/Pro); optional `ANTHROPIC_API_KEY` in `context-synthesizer/.env` for non-CLI clients.

**Dashboard:** `http://127.0.0.1:<PROXY_PORT>/dashboard` — per-turn billing split (cache read / write / uncached), four-layer payload, naive IDE history vs shaped context, cumulative $ saved, compaction timeline. See [DASHBOARD.md](DASHBOARD.md).

### Weekly (automatic)

On shared drive: `YYYY-MM-DD_handle_summary.md` + JSONL.

---

## Step 4 — Team lead weekly rollup

```bash
# On team lead machine (git checkout OK for lead, or install same way)
bash context-synthesizer/scripts/pull_from_drive.sh \
  'gdrive:Shared/ContextSynthesizer/weekly'

bash context-synthesizer/scripts/team_rollup.sh
```

Optional cron (Mondays 09:15):

```cron
15 9 * * 1 bash $HOME/.local/share/context-synthesizer/context-synthesizer/scripts/pull_from_drive.sh 'gdrive:Shared/ContextSynthesizer/weekly' && bash $HOME/.local/share/context-synthesizer/context-synthesizer/scripts/team_rollup.sh
```

---

## Backup zip import (team lead)

```bash
bash context-synthesizer/scripts/import_claude_backup.sh backup.zip --developer meet-chavda
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Download fails | Use `--tarball-file` from shared drive |
| No Monday upload | `~/.local/state/context-synthesizer/weekly-*.log` |
| Proxy `activating (auto-restart)` / exit 1 | See below |
| Proxy down | `systemctl --user restart context-synthesizer-proxy` |
| Reinstall | `bash install.sh --reinstall --developer ...` |

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
| `address already in use` / port 8080 | Often **Tabby** or another IDE plugin (`ss -tlnp \| grep 8080`). Use `PROXY_PORT=8081` in `context-synthesizer/.env`, `export SYNTH_PROXY_URL=http://127.0.0.1:8081`, run `configure_claude_proxy.sh`, then `install_proxy_service.sh` |
| `Claude.md not found` | Re-extract toolkit; file must exist at `context-synthesizer/Claude.md` |

Preflight helper: `bash context-synthesizer/scripts/check_proxy_ready.sh`

**Live dashboard:** `http://127.0.0.1:<PROXY_PORT>/dashboard` — billing bifurcation, L1–L4 layers, naive vs shaped, compactions. See [DASHBOARD.md](DASHBOARD.md).

---

## Script reference

| Script | Who |
|--------|-----|
| `install.sh` (repo root) | **Developer entry point** |
| `packaging/build-release-tarball.sh` | Team lead — build drive bundle |
| `scripts/setup_developer.sh` | Called by install.sh |
| `scripts/weekly_sync.sh` | Cron |
| `static/dashboard.html` + `/dashboard` | Live bifurcation UI (same port as proxy) |
| `scripts/pull_from_drive.sh` | Team lead |

More: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [CORPUS_COMPARATIVE_ANALYSIS.md](../reports/CORPUS_COMPARATIVE_ANALYSIS.md)
