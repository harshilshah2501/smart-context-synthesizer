# Developer onboarding — one installer, no git

**Time:** ~5 minutes once. No repository clone. After setup: **zero weekly chores**.

---

## Install (one command)

Ask your team lead for:

1. **rclone remote** path (shared drive), e.g. `gdrive:Shared/ContextSynthesizer/weekly`  
2. **Installer URL** — either GitHub raw or a file on the shared drive  

### Option A — curl from GitHub (simplest)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_GITHUB_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

Installs to `~/.local/share/context-synthesizer` — no git on your machine.

### Option B — shared drive tarball (no GitHub access)

Team lead uploads `context-synthesizer-toolkit-*.tar.gz` + `install.sh` to the drive.

```bash
# Download both files from drive, then:
bash install.sh \
  --tarball-file ~/Downloads/context-synthesizer-toolkit-2026.06.12.tar.gz \
  --developer YOUR_GITHUB_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

---

## What you get

| After setup | You do | Benefit |
|-------------|--------|---------|
| **`--enable-proxy`** | Use Claude Code normally | Live context compaction (background service) |
| **`--install-cron`** | Nothing weekly | `summary.md` auto-uploaded to shared drive every Monday |
| Both | Nothing | Full benefit — live + reports |

**Reports only** (no live proxy yet): drop `--enable-proxy`.

Evidence: [CORPUS_COMPARATIVE_ANALYSIS.md](../reports/CORPUS_COMPARATIVE_ANALYSIS.md).

---

## What the installer does

1. Downloads toolkit (or uses tarball) → `~/.local/share/context-synthesizer`  
2. Creates Python venv + dependencies  
3. Saves `~/.config/context-synthesizer/developer.env`  
4. **Optional proxy:** patches `~/.claude/settings.json`, starts user systemd service  
5. **Optional cron:** Monday 09:00 export + summary + rclone upload  

Smoke test:

```bash
bash ~/.local/share/context-synthesizer/context-synthesizer/scripts/weekly_sync.sh
```

---

## Prerequisites

| Item | Notes |
|------|-------|
| `python3`, `curl`, `tar` | Linux/macOS |
| `rclone` | For auto-upload — https://rclone.org/install/ |
| Claude Code | `~/.claude/projects/` populated by normal use |
| API key | Only if `--enable-proxy` — pasted once at install |

---

## Weekly report on shared drive

| File | You read |
|------|----------|
| `YYYY-MM-DD_you_summary.md` | Compression % on your longest session |
| `YYYY-MM-DD_you_claude.jsonl` | Team lead rollup |

---

## Cursor users

Add to the install command:

```bash
  --export-mode cursor --cursor-project your-cursor-project-slug
```

Live proxy is Claude Code only today.

---

## Uninstall

```bash
systemctl --user disable --now context-synthesizer-proxy 2>/dev/null || true
crontab -l 2>/dev/null | grep -v context-synthesizer-weekly | crontab - 2>/dev/null || true
rm -rf ~/.local/share/context-synthesizer ~/.config/context-synthesizer
# Remove ANTHROPIC_BASE_URL from ~/.claude/settings.json manually
```

---

## Team lead

[DEPLOY.md](DEPLOY.md) — build tarball, shared drive, rollup.
