# Developer onboarding

**Time:** ~5 minutes once. After setup: use Claude Code normally.

**Quick CLI:** [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · **Cost metrics:** [COST_SAVINGS.md](COST_SAVINGS.md)

---

## Install (GitHub or tarball)

### From git

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh your.handle
```

### From release tarball

```bash
tar -xzf context-synthesizer-toolkit-*.tar.gz
cd context-synthesizer-toolkit-*
bash run-setup.sh your.handle
```

Use a short developer id (e.g. email local-part: `jane.doe`).

**Live compaction (default ON):** Claude Code routes through a local proxy; Dreaming v4 compacts context during long sessions. Max/Pro login forwards auth — no API key at setup.

```bash
export PATH="$HOME/.local/bin:$PATH"
csynth doctor && csynth dashboard
```

**Proxy toggle:**

```bash
csynth proxy on | off | restart
```

---

## Optional: install from team shared drive

If your team publishes a synced folder (OneDrive, Google Drive, etc.):

```bash
cd /path/to/context-synthesizer-toolkit-latest
bash run-setup.sh your.handle
```

Team lead setup: [DEPLOY.md](DEPLOY.md) § Optional shared-drive publish.

---

Proxy and Claude Code run **inside WSL**. The live dashboard is served from WSL too.

**WSL systemd (once):** `/etc/wsl.conf` → `[boot]` / `systemd=true`, then `wsl --shutdown` from Windows and reopen WSL. Required for the proxy user service.

| Where | URL |
|-------|-----|
| **WSL terminal** (`curl`, Claude Code) | From `open_dashboard.sh` — `http://127.0.0.1:<PROXY_PORT>/dashboard?token=...` |
| **Windows Chrome/Edge** | From `open_dashboard.sh` — `http://<WSL_IP>:<PROXY_PORT>/dashboard?token=...` — **not** `127.0.0.1` |

WSL setup auto-generates **`DASHBOARD_TOKEN`** in `context-synthesizer/.env`. Always use URLs from `open_dashboard.sh`; do not bookmark `/dashboard` without `?token=`.

Helper (prints authenticated URLs; `--open` launches Windows browser):

```bash
bash context-synthesizer/scripts/open_dashboard.sh
bash context-synthesizer/scripts/open_dashboard.sh --open
```

If Windows shows **`ERR_EMPTY_RESPONSE`** but `curl` in WSL works → you hit the wrong localhost (often **Tabby on Windows :8080**). Use the WSL IP from `open_dashboard.sh`.

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

1. **[abraunegg/onedrive](https://github.com/abraunegg/onedrive)** — syncs SharePoint/OneDrive to e.g. `~/OneDrive`  
2. **IT-provided sync** — set path in `team.conf` → `SYNC_DIR`

### `team.conf` on Ubuntu

Edit `SYNC_DIR` to match **your** synced weekly folder, for example:

```bash
SYNC_DIR="$HOME/OneDrive/ContextSynthesizer/weekly"
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
| Live proxy + `/dashboard` | ✓ | ✓ (WSL — use WSL IP in Windows browser) |
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

## What you get (default via run-setup.sh)

| After setup | You do | Benefit |
|-------------|--------|---------|
| `ENABLE_PROXY=1` (default) | Use Claude Code normally | Live context compaction during sessions |
| `/dashboard` on proxy port | `csynth dashboard` while coding | Live bifurcation — cache/cost/layers/naive vs shaped |
| `csynth` on PATH | `csynth doctor`, `csynth logs` | Status, proxy toggle, troubleshooting |

---

## `csynth` commands (summary)

| Command | Purpose |
|---------|---------|
| `csynth status` | Proxy service + routing |
| `csynth proxy on` / `off` | Enable / disable synthesizer |
| `csynth dashboard` | Live cost & token dashboard URL |
| `csynth doctor` | Full routing preflight |
| `csynth logs` | Tail proxy journal |
| `csynth restart` | Restart proxy service |

**Reinstall:** `bash install.sh firstname.lastname --reinstall` from toolkit package root.

Full reference: [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md)

## Prerequisites

| Item | Notes |
|------|-------|
| `python3`, `curl`, `tar` | Linux / macOS / WSL |
| **OneDrive app** + synced team folder | Replaces rclone |
| Claude Code | `~/.claude/projects/` from normal use |
| Browser | Live dashboard — WSL IP in Windows browser; see `open_dashboard.sh` |

### Smoke test (live compaction + dashboard)

```bash
csynth status
csynth doctor
csynth dashboard
```

Or without `csynth` on PATH:

```bash
systemctl --user status context-synthesizer-proxy
bash context-synthesizer/scripts/check_proxy_ready.sh
bash context-synthesizer/scripts/open_dashboard.sh
bash context-synthesizer/scripts/verify_claude_routing.sh
```

Use Claude Code in a project — charts should update per API call. Badge top-left should show **live**.

**WSL + Claude Code on Windows (common):** setup configures **three** places when you run `configure_claude_proxy.sh`:
- WSL `~/.claude/settings.json` → `http://127.0.0.1:8080` (Claude CLI inside WSL)
- Windows `%USERPROFILE%\.claude\settings.json` → `http://<WSL_IP>:8080` (Claude desktop app)
- **VS Code** `%APPDATA%\Code\User\settings.json` → `claudeCode.environmentVariables` with `ANTHROPIC_BASE_URL`
  — **required for Claude Code in VS Code**; the extension does **not** read `~/.claude/settings.json`

After re-running configure, **restart VS Code** (or Claude Code panel). If the dashboard shows `proxy_requests: 0` but health checks pass:

```bash
csynth logs
# or: journalctl --user -u context-synthesizer-proxy -f | grep -E '\[ACCESS\]|\[PROXY\]'
```

Send one chat message in VS Code — you should see `[PROXY] → POST /v1/messages` in the journal. Cursor uses a different endpoint (`/v1/chat/completions`); that working does **not** prove VS Code is wired.

If the service won't start:

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
```

**`ModuleNotFoundError: anyio._backends`** (broken venv):

```bash
bash context-synthesizer/scripts/repair_venv.sh
csynth restart
```

**Port conflict (Tabby on 8080):**

```bash
echo 'PROXY_PORT=8081' >> context-synthesizer/.env
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
