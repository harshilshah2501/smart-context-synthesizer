# Deploying the Context Synthesizer

**Developers never clone git.** They run **`install.sh` once** (~5 min). After that: optional live proxy + automatic weekly uploads.

| Role | After setup |
|------|-------------|
| **Developer** | **0 min/week** (cron + background proxy) |
| **Team lead** | Pull drive → `team_rollup.sh` (~1 min/week) |

**Send developers:** [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)

---

## Motadata / SharePoint (no rclone)

1. Team lead: create or use shared folder  
   `ContextSynthesizer/weekly` on SharePoint (sync link in OneDrive).  
2. Each developer: open SharePoint link → **Sync** → note local path (usually `OneDrive - Motadata/...`).  
3. Developers run **one command** (no rclone, no API key, no proxy):

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer firstname.lastname \
  --sync-dir "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly" \
  --install-cron
```

Weekly files are **copied** into the synced folder; OneDrive uploads to SharePoint.

**Team lead rollup** (same synced folder on your machine):

```bash
bash context-synthesizer/scripts/pull_from_drive.sh \
  "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
bash context-synthesizer/scripts/team_rollup.sh
```

---

## Architecture

```text
install.sh (curl or drive)  →  ~/.local/share/context-synthesizer
                                        │
Claude Code ──► proxy (optional)        ├── weekly_sync.sh (cron)
~/.claude/projects/ ────────────────────┘         │
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

| Flag | Effect |
|------|--------|
| `--enable-proxy` | Live compaction during Claude Code sessions |
| `--install-cron` | Monday auto-export + upload |
| `--rclone-remote` | Shared drive destination |

---

## Step 2 — rclone (team lead, once)

1. Create `ContextSynthesizer/weekly/` on Google Drive (or S3).  
2. `rclone config` → remote name e.g. `gdrive`.  
3. Give developers the remote path: `gdrive:Shared/ContextSynthesizer/weekly`  
4. Each developer configures the **same remote name** on their machine (`rclone config` once).

---

## Step 3 — What developers see

### Live (`--enable-proxy`)

Claude Code unchanged — synthesizer runs as `context-synthesizer-proxy` user service.

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
| Proxy down | `systemctl --user restart context-synthesizer-proxy` |
| Reinstall | `bash install.sh --reinstall --developer ...` |

---

## Script reference

| Script | Who |
|--------|-----|
| `install.sh` (repo root) | **Developer entry point** |
| `packaging/build-release-tarball.sh` | Team lead — build drive bundle |
| `scripts/setup_developer.sh` | Called by install.sh |
| `scripts/weekly_sync.sh` | Cron |
| `scripts/pull_from_drive.sh` | Team lead |

More: [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [CORPUS_COMPARATIVE_ANALYSIS.md](../reports/CORPUS_COMPARATIVE_ANALYSIS.md)
