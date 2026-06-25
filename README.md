# Context Synthesizer

A local API proxy between **Claude Code** and **Cursor** and the Anthropic API. It compacts long session history into cached layers (L1/L2), preserves active tool loops, and exposes a live cost dashboard.

Open-source release — proxy + dashboard only. Internal team tooling lives in a separate private repository.

**Requires Anthropic** (Claude Code Max/Pro or Cursor with an Anthropic model). Prompt-cache economics use Anthropic `cache_control` breakpoints — not a generic OpenAI/Ollama proxy.

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

## Cache warmup (read this first)

The shipped starter `Claude.md` is ~380 tokens. Anthropic's prompt cache requires **≥1,024 tokens per `cache_control` block** on Sonnet-class models — so **low or zero `cache_read` on early turns is expected**, not a sign the proxy is broken.

| Phase | What you see |
|-------|----------------|
| Turns 1–9 | Layer 1 alone may be below the cache floor → little or no `cache_read` |
| Turn 10+ | Dreaming compaction merges history into Layer 2; prefix grows |
| Long sessions | **Cost vs payload** on the dashboard diverges — that is the primary success signal |

**Do not judge the proxy on turn-1 cache hits.** Watch `csynth dashboard` over a real coding session: compaction firing, payload stabilizing, and billed cost dropping relative to naive history growth.

**Production tip:** replace `context-synthesizer/Claude.md` with your project's architecture rules (aim ≥1,500 tokens). Verify with:

```bash
cd context-synthesizer
python3 count_tokens.py
```

More detail: [docs/guides/COST_SAVINGS.md](docs/guides/COST_SAVINGS.md) · [docs/guides/DEVELOPER_ONBOARDING.md](docs/guides/DEVELOPER_ONBOARDING.md#cache-warmup--what-success-looks-like)

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
