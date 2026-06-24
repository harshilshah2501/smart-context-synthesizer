# Deploying the Context Synthesizer

| Role | After setup |
|------|-------------|
| **Developer** | `bash run-setup.sh` or `bash install.sh` — use Claude Code normally |
| **Team lead** | Build tarball; optionally publish to a synced shared drive |

**Docs:** [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md)

---

## Build release tarball (all teams)

From `context-synthesizer/`:

```bash
bash packaging/build-release-tarball.sh
```

Output under `packaging/build/`:

```text
context-synthesizer-toolkit-YYYY.MM.DD/
context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
context-synthesizer-toolkit-latest.tar.gz
```

Distribute the folder or `.tar.gz` via GitHub Releases, internal file share, or optional OneDrive sync below.

Developers install:

```bash
tar -xzf context-synthesizer-toolkit-*.tar.gz
cd context-synthesizer-toolkit-*
bash run-setup.sh developer.id
```

---

## Optional: shared-drive publish (OneDrive / SharePoint)

For teams that sync a folder to all developers (enterprise rollout).

### One-time setup

```bash
cp packaging/share.conf.example packaging/share.conf
# edit SHARE_DIR_WIN / SHARE_DIR_WSL to your synced folder
```

### Every release

```bash
bash packaging/publish-to-sharepoint.sh
```

Copies `context-synthesizer-toolkit-latest/` + dated `.tar.gz` + `INSTALL.txt` to the configured share.  
`share.conf` is **gitignored** — never commit org paths.

The script:

1. Runs `packaging/build-release-tarball.sh`
2. Copies `context-synthesizer-toolkit-latest/` to your shared folder
3. Copies dated and `latest` `.tar.gz` archives
4. Writes `INSTALL.txt` at the share root

Share layout after publish:

```text
YourSharedDrive/Context-Synthesizer/
  context-synthesizer-toolkit-latest/
  context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
  context-synthesizer-toolkit-latest.tar.gz
  INSTALL.txt
```

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
ls -la /path/to/your/shared-drive/Context-Synthesizer/
# expect: context-synthesizer-toolkit-latest, *.tar.gz, INSTALL.txt
```

Tell developers after a release:

```text
1. Sync shared folder (or download tarball)
2. cd context-synthesizer-toolkit-latest
3. bash run-setup.sh developer.id
4. csynth doctor && csynth dashboard
```

---

## Developer — one command

Open terminal in the synced package folder:

```bash
cd context-synthesizer-toolkit-latest
bash run-setup.sh developer.id
```

Use Azure email local-part (`firstname.lastname`). No git or API key.

See `INSTALL.txt` at the share root or inside the package. **Live compaction is on by default.** Claude Code Max/Pro login forwards auth.

**Reinstall / upgrade** (after team lead publishes a new `context-synthesizer-toolkit-latest`):

```bash
cd context-synthesizer-toolkit-latest
bash install.sh developer.id --reinstall
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
  "$HOME/shared-drive/ContextSynthesizer/weekly"
bash context-synthesizer/scripts/team_rollup.sh
```

Optional team-lead cron (Mondays 09:15):

```cron
15 9 * * 1 bash /path/to/context-synthesizer-toolkit-latest/context-synthesizer/scripts/pull_from_drive.sh "$HOME/shared-drive/ContextSynthesizer/weekly" && bash /path/to/context-synthesizer-toolkit-latest/context-synthesizer/scripts/team_rollup.sh
```

---

## Architecture

```text
Team lead: publish-to-sharepoint.sh
              │
              ▼
    SharedDrive/Context-Synthesizer/  ──sync──►  team machines
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
| Reinstall | `bash install.sh developer.id --reinstall` from package root |

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
bash context-synthesizer/scripts/import_claude_backup.sh backup.zip --developer dev-id
```

---

## Alternative: GitHub / rclone

> **Enterprise teams:** optional `publish-to-sharepoint.sh` after configuring `share.conf`.

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
