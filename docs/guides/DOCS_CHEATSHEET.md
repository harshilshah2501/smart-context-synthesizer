# Documentation cheatsheet

One-page map: **which doc to open**, **which command to run**, **who it's for**.

---

## Start here (by role)

| I am… | Read first | Then |
|-------|------------|------|
| **Developer** (Motadata) | [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) | [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · [DASHBOARD.md](DASHBOARD.md) |
| **Team lead** | [DEPLOY.md](DEPLOY.md) | [TEAM_ANNOUNCEMENT.md](TEAM_ANNOUNCEMENT.md) · [DASHBOARD.md](DASHBOARD.md) |
| **R&D / architect** | [context_os_technical_report.md](../context_os_technical_report.md) | [SYNTHESIZER_RND_REPORT.md](../reports/SYNTHESIZER_RND_REPORT.md) |
| **Offline analysis only** | [Usage.md](Usage.md) | [CLI_STATS_GUIDE.md](CLI_STATS_GUIDE.md) |

---

## Guides — quick pick

| Doc | One line | Audience |
|-----|----------|----------|
| [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) | Install from SharePoint, WSL notes, smoke test | Developer |
| [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) | `csynth` — install, reinstall, proxy on/off, logs | Developer |
| [DEPLOY.md](DEPLOY.md) | Build tarball + `publish-to-sharepoint.sh` | Team lead |
| [DASHBOARD.md](DASHBOARD.md) | Live cost/token dashboard, WSL browser URLs | Everyone |
| [COST_SAVINGS.md](COST_SAVINGS.md) | Why **cost** drops when **payload** looks flat | Everyone |
| [TEAM_ANNOUNCEMENT.md](TEAM_ANNOUNCEMENT.md) | Copy-paste Slack/email rollout | Team lead |
| [Usage.md](Usage.md) | Offline modes A / C / D (no proxy) | Analyst |
| [CLI_STATS_GUIDE.md](CLI_STATS_GUIDE.md) | Mode A corpus import details | Analyst |
| [FETCH_BUNDLE.md](FETCH_BUNDLE.md) | Dev machine rsync from build server | Dev sync |
| [CURSOR_TEST.md](CURSOR_TEST.md) | Cursor IDE + OpenAI shim testing | Cursor users |

---

## Reports — quick pick

| Doc | One line |
|-----|----------|
| [SYNTHESIZER_RND_REPORT.md](../reports/SYNTHESIZER_RND_REPORT.md) | Full R&D record + roadmap |
| [COMPACTION_PROOF_REPORT.md](../reports/COMPACTION_PROOF_REPORT.md) | Turn-178 compaction deep dive |
| [CORPUS_COMPARATIVE_ANALYSIS.md](../reports/CORPUS_COMPARATIVE_ANALYSIS.md) | Three-developer corpus comparison |
| [BENCHMARK_ANALYSIS.md](../reports/BENCHMARK_ANALYSIS.md) | Internal proxy benchmark |
| [MEET_CHAVDA_CORPUS_REPORT.md](../reports/MEET_CHAVDA_CORPUS_REPORT.md) | meet-chavda (32 sessions) |
| [CHANDRESH_CORPUS_REPORT.md](../reports/CHANDRESH_CORPUS_REPORT.md) | chandresh corpus |
| [OM_CORPUS_REPORT.md](../reports/OM_CORPUS_REPORT.md) | om Org Mgmt (120 turns) |

---

## Command cheatsheet

### Developer — install & daily use

```bash
# Install (from synced SharePoint folder)
cd context-synthesizer-toolkit-latest
bash run-setup.sh firstname.lastname

# Reinstall / upgrade after team lead publishes
bash install.sh firstname.lastname --reinstall

# Proxy
csynth proxy on          # route Claude Code through synthesizer
csynth proxy off         # direct Anthropic API
csynth restart           # after errors or updates

# Status & debug
csynth status            # service + routing
csynth doctor            # full preflight
csynth dashboard         # live metrics URL
csynth logs              # tail proxy journal
```

### Team lead — publish release

```bash
cd context-synthesizer
# Edit packaging/share.conf once (OneDrive paths)
bash packaging/publish-to-sharepoint.sh
```

Manual build only:

```bash
bash packaging/build-release-tarball.sh
# → packaging/build/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
```

### Optional — weekly rollup

```bash
bash context-synthesizer/scripts/pull_from_drive.sh "$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
bash context-synthesizer/scripts/team_rollup.sh
```

---

## Common questions → doc

| Question | Open |
|----------|------|
| How do I install on Ubuntu 22.04? | [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) |
| How do I turn the proxy off temporarily? | [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) |
| Dashboard empty or 401? | [DASHBOARD.md](DASHBOARD.md) → Troubleshooting |
| Why is cost down but payload size similar? | [COST_SAVINGS.md](COST_SAVINGS.md) |
| How do I publish to SharePoint? | [DEPLOY.md](DEPLOY.md) |
| What do dashboard KPIs mean? | [DASHBOARD.md](DASHBOARD.md) · [COST_SAVINGS.md](COST_SAVINGS.md) |
| How does L1/L2/L3 compaction work? | [context_os_technical_report.md](../context_os_technical_report.md) |
| Offline corpus import (no proxy)? | [Usage.md](Usage.md) |
| Message for the team? | [TEAM_ANNOUNCEMENT.md](TEAM_ANNOUNCEMENT.md) |

---

## File locations (installed)

| Path | What |
|------|------|
| `~/.local/share/context-synthesizer/` | Installed toolkit + venv |
| `~/.local/bin/csynth` | CLI |
| `~/.config/context-synthesizer/developer.env` | Developer ID, proxy flag |
| `~/.claude/settings.json` | `ANTHROPIC_BASE_URL` when proxy on |
| `context-synthesizer/stats/telemetry.jsonl` | Persistent dashboard log |

---

## SharePoint layout (after publish)

```text
OneDrive - Motadata/Context-Synthesizer/
  context-synthesizer-toolkit-latest/     ← developers cd here
  context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
  context-synthesizer-toolkit-latest.tar.gz
  INSTALL.txt
```

---

## Doc tree (full index)

See [../README.md](../README.md) for the complete table of guides, reports, and architecture docs.
