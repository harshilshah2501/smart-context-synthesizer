# Smart Context Synthesizer

A local API proxy between **Claude Code** / **Cursor** and the Anthropic API. It compacts long session history into cached layers (L1/L2), preserves active tool loops, and exposes a live cost dashboard.

**Docs:** [docs/README.md](docs/README.md) · **Cheatsheet:** [docs/guides/DOCS_CHEATSHEET.md](docs/guides/DOCS_CHEATSHEET.md)

---

## Quick start

### From GitHub (recommended for open source)

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh your.handle --install-dir ~/.local/share/context-synthesizer
```

Or one-liner (public repo):

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- your.handle
```

Then:

```bash
export PATH="$HOME/.local/bin:$PATH"
csynth doctor && csynth dashboard
```

Use **Claude Code Max/Pro** — the CLI forwards OAuth; no separate API key at setup.

### From a release tarball

```bash
tar -xzf context-synthesizer-toolkit-*.tar.gz
cd context-synthesizer-toolkit-*
bash run-setup.sh your.handle
```

Team leads: `bash packaging/build-release-tarball.sh` — see [docs/guides/DEPLOY.md](docs/guides/DEPLOY.md).

---

## What it does

| Feature | Description |
|---------|-------------|
| **Layered compaction** | L1 rules + L2 ledger + L3 recent turns + L4 prompt |
| **Prompt cache alignment** | `cache_control` breakpoints on stable prefix |
| **Tool-faithful proxy** | Preserves `tool_use` / `tool_result` in active loops |
| **Pinned checkpoints** | `@synth-remember:` in user messages → L2a |
| **Live dashboard** | Cache read / uncached / cost bifurcation per request |
| **Dual API** | Anthropic `/v1/messages` + OpenAI `/v1/chat/completions` (Cursor) |

---

## Repository layout

```
.
├── README.md
├── docs/                     guides, reports, architecture
└── context-synthesizer/
    ├── proxy_tool.py         FastAPI gateway
    ├── proxy_message_bridge.py
    ├── compaction.py         Dreaming v4
    ├── scripts/csynth          post-install CLI
    ├── packaging/            tarball build (optional team publish scripts)
    └── stats/                local telemetry — gitignored, never commit
```

---

## Daily commands

```bash
csynth proxy on | off | restart
csynth status | doctor | dashboard | logs
```

Full reference: [docs/guides/CSYNTH_QUICK_REFERENCE.md](docs/guides/CSYNTH_QUICK_REFERENCE.md)

**Why cost drops when payload looks flat:** [docs/guides/COST_SAVINGS.md](docs/guides/COST_SAVINGS.md)

---

## Public release checklist

Before publishing or sharing forks, read [docs/guides/PUBLIC_RELEASE.md](docs/guides/PUBLIC_RELEASE.md).

**Never commit:** `.env`, `stats/`, `stats/backups/`, session exports, or org-specific `packaging/share.conf`.

---

## License

MIT — see [LICENSE](LICENSE). · Issues: [GitHub](https://github.com/harshilshah2501/smart-context-synthesizer)
