# Context Synthesizer

[![Project status](https://img.shields.io/badge/status-beta-orange)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/harshilshah2501/smart-context-synthesizer/actions/workflows/ci.yml/badge.svg)](https://github.com/harshilshah2501/smart-context-synthesizer/actions/workflows/ci.yml)

> **Context Synthesizer** is a local Claude Code/Cursor proxy that keeps long coding sessions cheaper and more coherent by combining prompt-cache-aligned context layers, tool-faithful recent turns, background compaction, pinned memory, and live cost telemetry.

A local API proxy between **Claude Code** and **Cursor** and the Anthropic API. It compacts long session history into cached layers (L1/L2), preserves active tool loops, and exposes a live cost dashboard.

**Fully self-contained** — this public repo is complete for install and daily use. No private repo required.

Open-source release — proxy + dashboard only. Internal team tooling lives in a separate private repository.

**Requires Anthropic** (Claude Code Max/Pro or Cursor with an Anthropic model). Prompt-cache economics use Anthropic `cache_control` breakpoints — not a generic OpenAI/Ollama proxy.

**Docs:** [docs/README.md](docs/README.md) · **Security:** [SECURITY.md](SECURITY.md) · **Cheatsheet:** [docs/guides/DOCS_CHEATSHEET.md](docs/guides/DOCS_CHEATSHEET.md)

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

The shipped starter `Claude.md` is a **production template (~1,600+ tokens)** — above Anthropic's **≥1,024-token cache minimum** on Sonnet-class models. You should see `cache_read` once the prefix warms, though Layer 2 still grows after compaction (~turn 10).

| Phase | What you see |
|-------|----------------|
| Turns 1–3 | Layer 1 template is cache-eligible; `cache_read` may still be zero until the prefix is written once |
| Turn 10+ | Dreaming compaction merges history into Layer 2; prefix grows further |
| Long sessions | **Cost vs payload** on the dashboard diverges — that is the primary success signal |

**Do not judge the proxy on turn-1 cache hits.** Watch `csynth dashboard` over a real coding session: compaction firing, payload stabilizing, and billed cost dropping relative to naive history growth.

**Customize for your project:** edit `context-synthesizer/Claude.md` (replace template tables). Verify with `python3 count_tokens.py`. Minimal stub: `Claude.minimal.md` (~380 tokens, below cache floor).

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
| **Dual API** | Anthropic `/v1/messages` (full fidelity) + OpenAI `/v1/chat/completions` (Cursor — see [limitations](#limitations)) |

---

## Project status

**Beta** — core proxy, compaction, and dashboard are production-tested locally, but behavior and APIs may evolve. See [CHANGELOG.md](CHANGELOG.md). Report issues on [GitHub](https://github.com/harshilshah2501/smart-context-synthesizer/issues).

---

## Limitations

| Topic | Detail |
|-------|--------|
| **Claude Code (recommended)** | `/v1/messages` path is tool-faithful — preserves `tool_use` / `tool_result` in active loops. |
| **Cursor / OpenAI shim** | `/v1/chat/completions` uses a simpler legacy payload builder — not full parity with the Anthropic path. Fine for chat + telemetry; not ideal for heavy tool loops. See [docs/guides/CURSOR_TEST.md](docs/guides/CURSOR_TEST.md). |
| **Sessions** | In-memory only — restart clears ledger and pins. |
| **Scale** | Single-machine local proxy — not horizontally scalable. |
| **Savings** | Cost reduction depends on session length, model pricing, and `Claude.md` size. Run `python test_simulator.py` for a reproducible local benchmark — avoid quoting fixed % savings without your own numbers. |
| **Anthropic-only economics** | Prompt-cache breakpoints require Anthropic API semantics. |

---

## Privacy & security

- **API keys** pass through to Anthropic per request; store them only in `.env` (gitignored).
- **Telemetry** (`stats/telemetry.jsonl`) and **pinned checkpoints** stay on your machine but may contain project text.
- **Dashboard** — default bind is `127.0.0.1`. If you use `PROXY_HOST=0.0.0.0`, set `DASHBOARD_TOKEN` or `DASHBOARD_LOCALHOST_ONLY=1`.

Full details: [SECURITY.md](SECURITY.md)

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

MIT — see [LICENSE](LICENSE). · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · Issues: [GitHub](https://github.com/harshilshah2501/smart-context-synthesizer)
