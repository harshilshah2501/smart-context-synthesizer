# Launch kit — HN, X, Reddit

Copy-paste templates for announcing **Context Synthesizer v0.1.0**.

**Repo:** https://github.com/harshilshah2501/smart-context-synthesizer  
**Release:** https://github.com/harshilshah2501/smart-context-synthesizer/releases/tag/v0.1.0

---

## Hacker News

### Title (pick one)

1. `Show HN: Context Synthesizer – local proxy that compacts Claude Code context and cuts API cost`
2. `Show HN: Context Synthesizer – MITM proxy for Claude Code with prompt-cache-aware compaction`
3. `Show HN: I built a local proxy to stop long Claude Code sessions from re-billing the same context`

Option 1 is the clearest for a general HN audience.

### Post body

> **Show HN: Context Synthesizer** — a local proxy between Claude Code / Cursor and the Anthropic API.
>
> Long coding sessions have a hidden cost: every turn re-sends the full transcript. Even with prompt caching, a growing history bloats the cached prefix and the uncached tail. Context Synthesizer sits in the middle and restructures each request before it hits Anthropic.
>
> **How it works**
>
> It assembles a four-layer payload on every request:
>
> - **L1** — stable project rules (`Claude.md`), pinned with `cache_control`
> - **L2** — compacted “history ledger” (semantic state, not raw chat)
> - **L3** — sliding window of recent turns
> - **L4** — current user prompt
>
> Session IDs go in HTTP headers (`X-Session-Id`), not in cached message bodies, so the prefix stays byte-stable for cache hits.
>
> Every ~10 turns (or 100K estimated history tokens), a background Haiku call compacts the rolling window into the ledger. Active tool loops (`tool_use` / `tool_result`) pass through verbatim so Claude Code doesn’t break mid-bash.
>
> You can pin facts that must survive compaction with `@synth-remember:` in a user message.
>
> **What you get**
>
> - Live dashboard: cache read / uncached / cost per request
> - `csynth` CLI: `doctor`, `dashboard`, `proxy on|off`, `logs`, `upgrade`
> - Works with Claude Code Max/Pro (OAuth forwarded — no API key at setup)
> - Cursor via OpenAI-compatible `/v1/chat/completions` shim
>
> **Install**
>
> ```bash
> git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
> cd smart-context-synthesizer/context-synthesizer
> bash install.sh your.handle
> csynth doctor && csynth dashboard
> ```
>
> Or tarball (no git): https://github.com/harshilshah2501/smart-context-synthesizer/releases/tag/v0.1.0
>
> **Honest limitations**
>
> - Anthropic-specific economics (`cache_control` breakpoints). Not a generic OpenAI/Ollama proxy.
> - Linux / WSL2 first (systemd user service for the proxy).
> - Compaction quality depends on Haiku synthesis — pinned checkpoints are the escape hatch.
> - First `cache_read` may be low until the prefix warms; judge long sessions on **cost vs payload**, not turn 1.
>
> MIT licensed. v0.1.0 tagged.
>
> Repo: https://github.com/harshilshah2501/smart-context-synthesizer  
> Architecture: `docs/context_os_technical_report.md`
>
> Happy to answer questions on the layering, cache math, or tool-faithful proxy design.

### First comment (post immediately after submitting)

> **Why not Claude Code’s built-in `/compact`?**  
> Native compaction is opaque, fires infrequently, and doesn’t structurally separate stable rules (L1) from compacted state (L2) from the active tool tail (L3). This proxy:
> 1. Keeps a fixed cached prefix (rules + ledger) across turns  
> 2. Compacts on a predictable schedule (every 10 turns or token threshold)  
> 3. Preserves active `tool_use`/`tool_result` blocks in the tail  
> 4. Shows you the cost bifurcation live on `/dashboard`  
>
> On long sessions we measured 90–99% counterfactual history compression vs sending the full transcript — but the main win is shrinking what enters the cached prefix, not enabling caching per se (Claude Code already caches well).

---

## Twitter / X

> Shipped v0.1.0 of Context Synthesizer — a local proxy for Claude Code that compacts session history into cache-friendly layers before each Anthropic API call.
>
> • L1 rules + L2 ledger = stable cached prefix  
> • Tool loops preserved verbatim  
> • Live cost dashboard  
> • `@synth-remember:` pins for facts that must survive compaction  
>
> MIT · Linux/WSL  
> https://github.com/harshilshah2501/smart-context-synthesizer

---

## Reddit (r/ClaudeAI or r/LocalLLaMA)

**Title:** `Open-source local proxy for Claude Code — compacts context into cache-friendly layers (v0.1.0)`

**Body:**

I built Context Synthesizer — a localhost proxy between Claude Code and Anthropic that:

- Restructures each request into 4 layers (rules → compacted ledger → recent turns → prompt)
- Runs background Haiku compaction every ~10 turns
- Keeps active tool_use/tool_result loops intact
- Shows live cache/cost metrics on a dashboard

Install:

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer && bash install.sh your.handle
```

Anthropic-specific (uses `cache_control`). Linux/WSL. MIT.

Release: https://github.com/harshilshah2501/smart-context-synthesizer/releases/tag/v0.1.0

Feedback welcome — especially on compaction quality in real multi-hour sessions.

---

## Posting tips

| Platform | When | Note |
|----------|------|------|
| **HN** | Tue–Thu, 9–11am US Eastern | Submit URL = GitHub repo; paste body as comment if title-only |
| **X** | Same day as HN | Link HN thread once live |
| **Reddit** | 24h after HN | Cross-post if HN discussion is active |

**Be ready to answer:** cache floor (1,024 tokens), session ID in headers, Haiku vs Sonnet for compaction, comparison to `rtk` / `claude-devtools`.
