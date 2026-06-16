# Smart Context Synthesizer

Offline R&D toolkit for **smart context compaction** — study long IDE sessions, estimate synthesizer-shaped payloads, and tune Dreaming rules.

**Team install:** SharePoint package + `bash run-setup.sh` → live proxy + **[dashboard](docs/guides/DASHBOARD.md)** at `http://127.0.0.1:<port>/dashboard`.

**Start here:** [context-synthesizer/README.md](context-synthesizer/README.md)  
**All docs:** [docs/README.md](docs/README.md)

## Repository layout

```
.
├── README.md                 ← you are here
├── docs/                     ← all documentation (guides, reports, architecture)
│   ├── guides/
│   ├── reports/
│   └── context_os_technical_report.md
└── context-synthesizer/
    ├── *.py                  ← import pipeline, compaction, gateway
    ├── scripts/
    ├── packaging/            ← deprecated .deb (legacy)
    └── stats/                ← local corpora (gitignored)
```

## Quick start (developers — no git)

**SharePoint / Motadata package (recommended):** `bash run-setup.sh firstname.lastname` — live compaction on by default (`ENABLE_PROXY=1` in `team.conf`).

**curl / rclone:**

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
  --developer YOUR_HANDLE \
  --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
  --enable-proxy \
  --install-cron
```

Team lead: [docs/guides/DEPLOY.md](docs/guides/DEPLOY.md) · Developers: [docs/guides/DEVELOPER_ONBOARDING.md](docs/guides/DEVELOPER_ONBOARDING.md) · Live metrics: [docs/guides/DASHBOARD.md](docs/guides/DASHBOARD.md)

## What is not in this repo

| Path | Reason |
|------|--------|
| `m-coder-core/`, `Ollama/` | Unrelated projects (gitignored) |
| `context-synthesizer/stats/` | Session JSONL — sensitive, local only |
| `*.zip` backups | Session exports — never commit |
| `docs/notes/` | Personal scratch notes (gitignored) |

GitHub: [harshilshah2501/smart-context-synthesizer](https://github.com/harshilshah2501/smart-context-synthesizer)
