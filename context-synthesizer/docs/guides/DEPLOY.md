# Deploying the Context Synthesizer (Phase 3)

**What you are deploying:** an offline weekly corpus pipeline — not a server, not a `.deb`, not a live proxy.

Each developer runs a local script that reads IDE session logs from disk and produces JSONL exports. The team lead aggregates those files to tune the synthesizer (Dreaming rules, compaction thresholds).

| Role | Does what | Time |
|------|-----------|------|
| **Developer** | Run `export_weekly_corpus.sh` once a week | ~30 s |
| **Team lead** | Collect exports → `team_rollup.sh` | ~1 min |
| **Optional** | `run_phase2_validation.py` after importer changes | ~3 min |

---

## Architecture

```text
Developer machine                         Team lead
─────────────────                         ─────────
~/.claude/projects/  ──┐
~/.cursor/projects/  ──┼── export_weekly_corpus.sh
                       │         │
                       ▼         ▼
              stats/weekly/2026-06-10_alice_claude.jsonl
              stats/weekly/2026-06-10_alice_hot_claude.json
                       │
                       │  upload (Slack / Drive / git-ignored inbox)
                       ▼
              stats/inbox/*.jsonl  ──►  team_rollup.sh  ──►  reports/
```

**No API key. No network at export time.** Session logs never leave the machine unless the developer uploads the generated JSONL/CSV.

---

## Step 1 — One-time setup (each machine)

### Option A — clone + setup script (recommended)

```bash
git clone <your-repo-url> ~/Out-of-bound-chronicles
cd ~/Out-of-bound-chronicles
bash context-synthesizer/scripts/setup.sh
```

### Option B — already have the repo

```bash
cd ~/Out-of-bound-chronicles
bash context-synthesizer/scripts/setup.sh
```

Set your handle once (used in JSONL `developer_id`):

```bash
export TELEMETRY_DEVELOPER_ID="your-github-handle"
# Add to ~/.bashrc or ~/.zshrc to persist
```

---

## Step 2 — Weekly export (developers)

### Claude Max / Pro → Mode D (recommended)

```bash
cd ~/Out-of-bound-chronicles
export TELEMETRY_DEVELOPER_ID="your-github-handle"

bash context-synthesizer/scripts/export_weekly_corpus.sh --mode d
```

Produces under `context-synthesizer/stats/weekly/`:

| File | Purpose |
|------|---------|
| `YYYY-MM-DD_<handle>_claude.jsonl` | Full corpus for team rollup |
| `YYYY-MM-DD_<handle>_claude.csv` | Spreadsheet-friendly summary |
| `YYYY-MM-DD_<handle>_hot_claude.json` | Largest session deep-dive |

**Prerequisite:** use Claude Code in at least one project so `~/.claude/projects/` exists.

### Cursor IDE → Mode C

```bash
bash context-synthesizer/scripts/export_weekly_corpus.sh \
  --mode cursor --project your-repo-slug
```

Project slug matches the folder name under `~/.cursor/projects/` (e.g. `m-coder` → `home-harshil-Harshil-PoCs-m-coder`).

### Quick token snapshot → Mode A

```bash
bash context-synthesizer/scripts/export_weekly_corpus.sh --mode a
```

### Both Claude + Cursor

```bash
bash context-synthesizer/scripts/export_weekly_corpus.sh --mode all --project m-coder
```

---

## Step 3 — Upload to team lead

`stats/` is **gitignored** (session data stays local). Pick one delivery channel:

| Channel | How |
|---------|-----|
| **Shared Drive / S3** | Upload `stats/weekly/YYYY-MM-DD_<handle>_*` |
| **Slack / email** | Attach JSONL + CSV (small; hot JSON optional) |
| **Monorepo inbox** | Copy into lead's `context-synthesizer/stats/inbox/` |

Minimum upload per developer per week: **one `*_claude.jsonl` or `*_cursor.jsonl`**.

---

## Step 4 — Team lead rollup

Copy all developer uploads into the inbox, then:

```bash
cd ~/Out-of-bound-chronicles
cp /path/from/drive/*.jsonl context-synthesizer/stats/inbox/

bash context-synthesizer/scripts/team_rollup.sh
```

Output: `context-synthesizer/stats/reports/YYYY-MM-DD_team_report.csv` plus stdout from `collect_stats.py` (corpus insights block).

### With Phase 2 regression (optional)

After importer or `compaction.py` changes:

```bash
bash context-synthesizer/scripts/team_rollup.sh --validate
```

Requires a baseline corpus at `stats/meet-chavda_corpus.jsonl` (or pass a custom baseline to `run_phase2_validation.py`).

---

## Special case — Claude backup zip (no live CLI on lead machine)

When a developer shares a `~/.claude` backup instead of running export locally:

```bash
bash context-synthesizer/scripts/import_claude_backup.sh \
  path/to/claude-folder-backup.zip \
  --developer meet-chavda
```

This unzips to `stats/backups/<developer>/`, imports Mode D, and writes dated files to `stats/weekly/`.

---

## Cron / automation (optional)

Add to crontab for hands-off Monday export:

```cron
0 9 * * 1 cd /home/you/Out-of-bound-chronicles && TELEMETRY_DEVELOPER_ID=you bash context-synthesizer/scripts/export_weekly_corpus.sh --mode d >> /tmp/corpus-export.log 2>&1
```

Upload step still needs a separate sync (rclone, Drive CLI, etc.) if you want full automation.

---

## What is NOT part of Phase 3 deploy

| Item | Status |
|------|--------|
| `proxy_tool.py` live gateway | Implementation target only — team does **not** route traffic |
| Ubuntu `.deb` | Deprecated |
| `ANTHROPIC_API_KEY` / `test_simulator.py` | Optional internal gateway benchmark |
| Production `Claude.md` (~200K tokens) | Future — use `build_production_claude_md.py` when ready |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `~/.claude/projects` not found | Run Claude Code in a project directory first |
| Empty Cursor import | Check `--project` slug matches `~/.cursor/projects/*` |
| `No module named …` | Re-run `scripts/setup.sh` |
| Low compression on short sessions | Normal for 100–110 turn Cursor sessions; focus on 200+ turn sessions |
| Permission denied on scripts | `chmod +x context-synthesizer/scripts/*.sh` |

---

## File reference

| Script | Who |
|--------|-----|
| `scripts/setup.sh` | Everyone (once) |
| `scripts/export_weekly_corpus.sh` | Developers (weekly) |
| `scripts/import_claude_backup.sh` | Team lead (backup imports) |
| `scripts/team_rollup.sh` | Team lead (weekly) |
| `run_phase2_validation.py` | Team lead (after code changes) |

More detail: [Usage.md](guides/Usage.md) · [PHASE_2_REPORT.md](reports/PHASE_2_REPORT.md) · [SYNTHESIZER_RND_REPORT.md](reports/SYNTHESIZER_RND_REPORT.md)
