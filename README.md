# Smart Context Synthesizer

Offline R&D toolkit for **smart context compaction** — study long IDE sessions, estimate synthesizer-shaped payloads, and tune Dreaming rules.

**Start here:** [context-synthesizer/README.md](context-synthesizer/README.md)

## Repository layout

```
.
├── README.md                          ← you are here
├── docs/
│   └── context_os_technical_report.md ← gateway design (proxy_tool.py)
└── context-synthesizer/
    ├── *.py                           ← import pipeline, compaction, gateway
    ├── scripts/                       ← setup, weekly export, team rollup
    ├── docs/
    │   ├── guides/                    ← Usage, DEPLOY, CLI_STATS_GUIDE
    │   └── reports/                   ← R&D reports, proof studies, corpus notes
    ├── packaging/                     ← deprecated .deb (legacy)
    └── stats/                         ← local corpora (gitignored)
```

## Quick start

```bash
cd ~/Out-of-bound-chronicles
bash context-synthesizer/scripts/setup.sh
bash context-synthesizer/scripts/export_weekly_corpus.sh --mode d
```

## What is not in this repo

| Path | Reason |
|------|--------|
| `m-coder-core/`, `Ollama/` | Unrelated projects (gitignored) |
| `context-synthesizer/stats/` | Session JSONL — sensitive, local only |
| `*.zip` backups | Session exports — never commit |
| `docs/notes/` | Personal scratch notes (gitignored) |

GitHub: [harshilshah2501/smart-context-synthesizer](https://github.com/harshilshah2501/smart-context-synthesizer)
