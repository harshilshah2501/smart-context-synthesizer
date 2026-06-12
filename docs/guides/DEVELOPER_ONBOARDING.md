# Developer onboarding — one installer, no git

**Time:** ~5 minutes once. After setup: **zero weekly chores**.

---

## Motadata / SharePoint (no rclone, no API key)

> **The GitHub repo is private** — `curl raw.githubusercontent.com/.../install.sh` returns **404**.  
> Use **install.sh from SharePoint** (team lead uploads it once).

You need **OneDrive desktop** syncing the team folder (open the SharePoint link → **Sync**).

Team lead puts on SharePoint (e.g. `ContextSynthesizer/`):

- `install.sh`
- `context-synthesizer-toolkit-YYYY.MM.DD.tar.gz` (from `packaging/build-release-tarball.sh`)

### Linux / WSL (after OneDrive sync)

```bash
bash "$HOME/OneDrive - Motadata/ContextSynthesizer/install.sh" \
  --tarball-file "$HOME/OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.12.tar.gz" \
  --developer firstname.lastname \
  --sync-dir "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly" \
  --install-cron
```

### Windows (Git Bash)

Same paths under `$HOME/OneDrive - Motadata/...` or `/mnt/c/Users/<you>/OneDrive - Motadata/...` in WSL.

Use your **Azure email local-part** for `--developer` (e.g. `harshil.shah` for `harshil.shah@motadata.com`).

**No `--enable-proxy`** — corporate Claude has no personal API key. You get **automatic weekly reports** on SharePoint; live compaction is not enabled.

**How upload works:** cron copies files into your local OneDrive folder → OneDrive app syncs to SharePoint. No rclone.

Adjust `--sync-dir` if your OneDrive path differs (check in file manager after Sync).

---

## Install (generic)

### curl from GitHub (public repo only)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_ID \
  --sync-dir "/path/to/onedrive/ContextSynthesizer/weekly" \
  --install-cron
```

Private repo → use SharePoint `install.sh` + `--tarball-file` (see above).

### With rclone (optional)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_ID \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --install-cron
```

---

## What you get (Motadata default)

| After setup | You do | Benefit |
|-------------|--------|---------|
| `--install-cron` + `--sync-dir` | Nothing weekly | `summary.md` + JSONL appear on SharePoint every Monday |
| `--enable-proxy` | Not used | Requires personal API key |

---

## Prerequisites

| Item | Notes |
|------|-------|
| `python3`, `curl`, `tar` | Linux / macOS / WSL |
| **OneDrive app** + synced team folder | Replaces rclone |
| Claude Code | `~/.claude/projects/` from normal use |

Smoke test:

```bash
bash ~/.local/share/context-synthesizer/context-synthesizer/scripts/weekly_sync.sh
```

Check files appear in your OneDrive `ContextSynthesizer/weekly` folder.

---

## Team lead

[DEPLOY.md](DEPLOY.md) — SharePoint folder setup, rollup from same synced folder.
