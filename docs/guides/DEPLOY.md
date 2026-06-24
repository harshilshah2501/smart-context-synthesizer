# Deploying the Context Synthesizer

**Developers never clone git.** They run **`run-setup.sh` once** (~5 min) from the SharePoint package. After that: **live compaction proxy** (primary) + optional weekly SharePoint uploads.

| Role | After setup |
|------|-------------|
| **Developer** | Use Claude Code normally (proxy runs in background); `csynth proxy on\|off` as needed |
| **Team lead** | Publish releases to SharePoint; optional weekly `team_rollup.sh` (~1 min/week) |

**Send developers:** [TEAM_ANNOUNCEMENT.md](TEAM_ANNOUNCEMENT.md) · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · [DASHBOARD.md](DASHBOARD.md) · [COST_SAVINGS.md](COST_SAVINGS.md)

> **Motadata teams:** use only the section below. Skip [Alternative: GitHub / rclone](#alternative-github--rclone).

---

## Motadata / SharePoint — team lead publish (recommended)

> **Repo is private** — do not ask developers to `curl` from GitHub.  
> **One command** builds the toolkit and copies it to your synced OneDrive folder → SharePoint updates automatically.

### One-time setup (team lead machine)

1. **Clone or sync** the repo on a machine with OneDrive sync to SharePoint:
   ```bash
   git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
   cd smart-context-synthesizer/context-synthesizer
   ```

2. **Edit `packaging/share.conf` once** if your OneDrive path differs:
   ```bash
   # packaging/share.conf
   SHARE_DIR_WIN='C:\Users\Harshil Shah\OneDrive - Motadata\Context-Synthesizer'
   SHARE_DIR_WSL='/mnt/c/Users/Harshil Shah/OneDrive - Motadata/Context-Synthesizer'
   LATEST_NAME='context-synthesizer-toolkit-latest'
   ```

3. **Create the SharePoint folder** in OneDrive (if missing):
   `OneDrive - Motadata/Context-Synthesizer/`

4. **Share the SharePoint link** with the team → developers click **Sync** in OneDrive.

### Every release — build + copy to shared drive

From the `context-synthesizer` directory (repo checkout or dev copy):

```bash
bash packaging/publish-to-sharepoint.sh
```

This script:

1. Runs `packaging/build-release-tarball.sh` (creates dated toolkit under `packaging/build/`)
2. Copies **`context-synthesizer-toolkit-latest/`** → your OneDrive `Context-Synthesizer/` folder
3. Copies **`context-synthesizer-toolkit-YYYY.MM.DD.tar.gz`** (dated archive)
4. Copies **`context-synthesizer-toolkit-latest.tar.gz`** (stable archive name)
5. Writes **`INSTALL.txt`** at the share root with developer instructions

**No manual upload. No `install.sh` edits per release.**

OneDrive syncs to SharePoint within minutes. Developers always use the stable folder name:

```text
OneDrive - Motadata/Context-Synthesizer/
  context-synthesizer-toolkit-latest/     ← always current (recommended)
  context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
  context-synthesizer-toolkit-latest.tar.gz
  INSTALL.txt
```

### Manual build only (without OneDrive copy)

If you need the tarball locally without publishing:

```bash
bash packaging/build-release-tarball.sh
```

Output:

```text
context-synthesizer/packaging/build/
  context-synthesizer-toolkit-YYYY.MM.DD/          # extracted package
  context-synthesizer-toolkit-YYYY.MM.DD.tar.gz    # dated archive
  context-synthesizer-toolkit-latest.tar.gz        # symlink to latest .tar.gz
```

Then upload manually to SharePoint if `publish-to-sharepoint.sh` cannot reach your OneDrive path.

### What gets built

The toolkit package includes:

| Path in package | Contents |
|-----------------|----------|
| `run-setup.sh` | Developer entry point |
| `install.sh` | Install / `--reinstall` |
| `INSTALL.txt` | Quick install card |
| `docs/` | Guides (onboarding, dashboard, cost savings, `csynth`) |
| `context-synthesizer/` | Proxy, dashboard, scripts, compaction |

`team.conf` in the built package sets `ENABLE_PROXY=1` by default. Weekly cron is **not** enabled by default.

### Verify publish

```bash
ls -la "/mnt/c/Users/Harshil Shah/OneDrive - Motadata/Context-Synthesizer/"
# expect: context-synthesizer-toolkit-latest, *.tar.gz, INSTALL.txt
```

Tell developers after a release:

```text
1. OneDrive → Sync Context-Synthesizer (or wait for auto-sync)
2. cd context-synthesizer-toolkit-latest
3. bash run-setup.sh firstname.lastname
4. csynth doctor && csynth dashboard
```

---

## Developer — one command

Open terminal in the synced package folder:

```bash
cd context-synthesizer-toolkit-latest
bash run-setup.sh harshil.shah
```

Use Azure email local-part (`firstname.lastname`). No git or API key.

See `INSTALL.txt` at the share root or inside the package. **Live compaction is on by default.** Claude Code Max/Pro login forwards auth.

**Reinstall / upgrade** (after team lead publishes a new `context-synthesizer-toolkit-latest`):

```bash
cd context-synthesizer-toolkit-latest
bash install.sh firstname.lastname --reinstall
csynth doctor
```

**Proxy toggle** (no reinstall): `csynth proxy on` · `csynth proxy off` · `csynth restart`

Full CLI reference: [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md)

---

## Optional: weekly team rollup

Weekly export cron is **optional** (`ENABLE_WEEKLY_CRON=1` in `team.conf` before build, or run `weekly_sync.sh` manually).

When developers upload weekly summaries to the synced folder:

```bash
bash context-synthesizer/scripts/pull_from_drive.sh \
  "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
bash context-synthesizer/scripts/team_rollup.sh
```

Optional team-lead cron (Mondays 09:15):

```cron
15 9 * * 1 bash /path/to/context-synthesizer-toolkit-latest/context-synthesizer/scripts/pull_from_drive.sh "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly" && bash /path/to/context-synthesizer-toolkit-latest/context-synthesizer/scripts/team_rollup.sh
```

---

## Architecture

```text
Team lead: publish-to-sharepoint.sh
              │
              ▼
    OneDrive/Context-Synthesizer/  ──sync──►  SharePoint
              │
Developer: run-setup.sh / install.sh
              │
Claude Code ──► proxy (default ON) ────────►  /dashboard  (live bifurcation UI)
~/.claude/projects/ ───────────────────────►  weekly_sync.sh (optional)
              │
              ▼
    pull_from_drive.sh → team_rollup.sh  (team lead, optional)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Share folder not found` on publish | Fix paths in `packaging/share.conf`; ensure OneDrive folder exists and is synced |
| Publish works but devs see old version | Wait for OneDrive sync; confirm `context-synthesizer-toolkit-latest` timestamp |
| Setup fails at proxy step | Enable systemd (WSL: `[boot] systemd=true` in `/etc/wsl.conf`, then `wsl --shutdown`) |
| Proxy down | `csynth restart` |
| Reinstall | `bash install.sh firstname.lastname --reinstall` from package root |

### Proxy won't start (exit-code / auto-restart)

```bash
csynth logs
# or:
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
```

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | `bash context-synthesizer/scripts/repair_venv.sh` then `csynth restart` |
| Port 8080 busy (Tabby, etc.) | `PROXY_PORT=8081` in `context-synthesizer/.env`, re-run `configure_claude_proxy.sh` |
| Upstream 502 | `csynth logs` — look for `[PROXY] ✗ upstream error` |

Preflight: `csynth doctor` · `bash context-synthesizer/scripts/check_proxy_ready.sh`

---

## Script reference

| Script | Who |
|--------|-----|
| **`packaging/publish-to-sharepoint.sh`** | **Team lead — build + copy to OneDrive (primary)** |
| `packaging/build-release-tarball.sh` | Team lead — build only |
| `packaging/share.conf` | Team lead — OneDrive paths (edit once) |
| `run-setup.sh` (package root) | **Developer entry point** |
| `install.sh` (package root) | Install / `--reinstall` |
| `scripts/csynth` | Developer CLI — proxy, dashboard, logs |
| `scripts/setup_developer.sh` | Called by install.sh |
| `scripts/weekly_sync.sh` | Optional cron |
| `scripts/pull_from_drive.sh` | Team lead rollup |
| `scripts/team_rollup.sh` | Team lead rollup |

More: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · `INSTALL.txt` at the SharePoint share root

---

## Backup zip import (team lead)

```bash
bash context-synthesizer/scripts/import_claude_backup.sh backup.zip --developer meet-chavda
```

---

## Alternative: GitHub / rclone

> **Not for Motadata rollout.** Use SharePoint + `publish-to-sharepoint.sh` above.

### Publish installer (public repo only)

```text
https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh
```

Or build tarball manually:

```bash
bash packaging/build-release-tarball.sh
# Upload .tar.gz to shared drive
```

### Developer install (rclone)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer THEIR_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy
```

| Flag / `team.conf` | Effect |
|--------------------|--------|
| `ENABLE_PROXY=1` / `--enable-proxy` | Live compaction (**default** in `run-setup.sh`) |
| `ENABLE_WEEKLY_CRON=1` / `--install-cron` | Monday auto-export (optional, not default) |
| `--sync-dir` / `SYNC_DIR` | OneDrive folder for weekly upload |

### Team lead weekly rollup (rclone)

```bash
bash context-synthesizer/scripts/pull_from_drive.sh 'gdrive:Shared/ContextSynthesizer/weekly'
bash context-synthesizer/scripts/team_rollup.sh
```
