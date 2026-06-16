# Developer onboarding — one installer, no git

**Time:** ~5 minutes once. After setup: use Claude Code normally; optional zero weekly chores.

---

## Motadata — install from shared package (simplest)

Team lead shares **one folder** on SharePoint (the built toolkit package).  
You **Sync** it in OneDrive, then run **one command**:

```bash
cd "/path/to/OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-YYYY.MM.DD"
bash run-setup.sh firstname.lastname
```

Example:

```bash
bash run-setup.sh harshil.shah
```

Read `INSTALL.txt` in the same folder. No GitHub, no rclone.

Use your **Azure email local-part** for `--developer` (e.g. `harshil.shah` for `harshil.shah@motadata.com`).

**Primary benefit — live compaction (on by default):** Claude Code routes through a local proxy; Dreaming v4 compacts context during long sessions. Log in to Claude Code (Max/Pro) as usual — the CLI forwards auth to the proxy; no separate API key at setup.

**Live dashboard:** open `http://127.0.0.1:8080/dashboard` (or `:8081` if `PROXY_PORT=8081` in `context-synthesizer/.env`) to see **where savings come from** — billing bifurcation, L1–L4 layers, naive vs shaped context, compactions. Updates automatically as you code. Full guide: [DASHBOARD.md](DASHBOARD.md).

**Optional — weekly SharePoint reports:** Monday cron copies session summaries to your synced folder for team rollup (`ENABLE_WEEKLY_CRON=1` in `team.conf`).

**How upload works:** cron copies files into your local OneDrive folder → OneDrive app syncs to SharePoint. No rclone.

Adjust `--sync-dir` if your OneDrive path differs (check in file manager after Sync).

---

## Ubuntu Linux (native, not WSL)

**Install command is the same** — `bash run-setup.sh firstname.lastname`.  
The toolkit targets Linux first (cron, systemd, `~/.claude/projects/`).

### Prerequisites (once per machine)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### Getting the package onto Ubuntu

| Method | How |
|--------|-----|
| **OneDrive sync** (best for auto-upload) | Install a OneDrive client, sync the SharePoint folder, run `run-setup.sh` from the synced package path |
| **Download tarball** | Get `context-synthesizer-toolkit-*.tar.gz` from SharePoint in the browser → extract → `bash run-setup.sh` |

Ubuntu has **no Microsoft OneDrive desktop app** like Windows. Common options:

1. **[abraunegg/onedrive](https://github.com/abraunegg/onedrive)** — syncs SharePoint/OneDrive to e.g. `~/OneDrive` or `~/OneDrive - Motadata`  
2. **IT-provided sync** — if Motadata mounts the folder elsewhere, set that path in `team.conf` → `SYNC_DIR`

### `team.conf` on Ubuntu

Edit `SYNC_DIR` to match **your** synced weekly folder, for example:

```bash
SYNC_DIR="$HOME/OneDrive/ContextSynthesizer/weekly"
# or, if the client uses the Motadata label:
SYNC_DIR="$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
```

Then:

```bash
cd ~/OneDrive/ContextSynthesizer/context-synthesizer-toolkit-YYYY.MM.DD
bash run-setup.sh firstname.lastname
```

### Ubuntu vs Windows — what is identical

| Piece | Ubuntu | Windows |
|-------|--------|---------|
| `run-setup.sh` | ✓ | ✓ (Git Bash / WSL) |
| Live proxy + `/dashboard` | ✓ | ✓ (WSL) |
| Weekly cron | ✓ (`cron`) | ✓ (WSL cron or Task Scheduler — cron via WSL) |
| Claude Code logs | `~/.claude/projects/` | Same in WSL; native Windows path differs |
| Weekly upload | Copy → synced folder | Copy → OneDrive app syncs |

**Without any OneDrive sync on Ubuntu**, install still works, but Monday uploads stay local unless you add sync (onedrive client or ask IT for a shared mount).

---

## Install (generic)

### curl from GitHub (public repo only)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_ID \
  --sync-dir "/path/to/onedrive/ContextSynthesizer/weekly" \
  --enable-proxy \
  --install-cron
```

Private repo → use SharePoint package + `run-setup.sh` (see above).

### With rclone (optional)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_ID \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

---

## What you get (default via run-setup.sh / team.conf)

| After setup | You do | Benefit |
|-------------|--------|---------|
| `ENABLE_PROXY=1` (default) | Use Claude Code normally | Live context compaction during sessions |
| `/dashboard` on proxy port | Open in browser while coding | Live bifurcation — cache/cost/layers/naive vs shaped |
| `ENABLE_WEEKLY_CRON=1` (default) | Nothing weekly | `summary.md` + JSONL on SharePoint every Monday |

---

## Prerequisites

| Item | Notes |
|------|-------|
| `python3`, `curl`, `tar` | Linux / macOS / WSL |
| **OneDrive app** + synced team folder | Replaces rclone |
| Claude Code | `~/.claude/projects/` from normal use |
| Browser | For live dashboard (local only — `127.0.0.1`) |

### Smoke test (live compaction + dashboard)

```bash
systemctl --user status context-synthesizer-proxy
bash context-synthesizer/scripts/check_proxy_ready.sh

# Dashboard (8081 if Tabby or another app uses 8080)
open http://127.0.0.1:8080/dashboard
# or: grep PROXY_PORT context-synthesizer/.env
```

Use Claude Code in a project — charts should update per API call. Badge top-left should show **live**.

If the service won't start:

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
```

**Port conflict (Tabby on 8080):**

```bash
echo 'PROXY_PORT=8081' >> context-synthesizer/.env
export SYNTH_PROXY_URL=http://127.0.0.1:8081
bash context-synthesizer/scripts/configure_claude_proxy.sh
bash context-synthesizer/scripts/install_proxy_service.sh
```

### Optional weekly upload test

```bash
bash context-synthesizer/scripts/weekly_sync.sh
```

---

## Team lead

[DEPLOY.md](DEPLOY.md) — SharePoint folder setup, rollup from same synced folder.
