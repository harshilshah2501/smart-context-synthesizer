# Context Synthesizer

A local API proxy between **Claude Code** and **Cursor** and the Anthropic API. It compacts long session history into cached layers (L1/L2), preserves active tool loops, and exposes a live cost dashboard.

Open-source release — proxy + dashboard only. Internal team tooling lives in a separate private repository.

**Docs:** [docs/README.md](docs/README.md) · **Cheatsheet:** [docs/guides/DOCS_CHEATSHEET.md](docs/guides/DOCS_CHEATSHEET.md)

---

## Quick start

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh your.handle
```

Or one-liner:

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

Build a tarball from this branch: [docs/guides/RELEASE.md](docs/guides/RELEASE.md).

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
├── docs/                     user guides + architecture
└── context-synthesizer/
    ├── proxy_tool.py         FastAPI gateway
    ├── proxy_message_bridge.py
    ├── compaction.py         Dreaming v4
    ├── scripts/csynth        post-install CLI
    ├── packaging/            release tarball build
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

## Repositories

| Repository | Visibility | Contents |
|------------|------------|----------|
| [smart-context-synthesizer](https://github.com/harshilshah2501/smart-context-synthesizer) | **Public** | Proxy product, install, user docs |
| `smart-context-synthesizer-internal` | **Private** | Team deploy, corpus tooling, internal reports |

---

## License

MIT — see [LICENSE](LICENSE). · Issues: [GitHub](https://github.com/harshilshah2501/smart-context-synthesizer)
