# Live telemetry dashboard

Real-time bifurcation of **where the Context Synthesizer saves tokens and cost** — served by the same proxy process as Claude Code traffic.

**URL:** `http://127.0.0.1:<PROXY_PORT>/dashboard` (default port `8080`, or `8081` if configured in `context-synthesizer/.env`)

---

## What you see

| Section | Shows |
|---------|--------|
| **KPI cards** | Requests, compactions, $ saved, compression vs naive IDE history, cache read %, uncached tail %, IDE bloat ratio |
| **Billing bifurcation** | Per turn: `cache_read` / `cache_write` / `uncached` tokens (Anthropic billing buckets) |
| **Four-layer payload** | Est. L1 (rules) / L2 (ledger) / L3 (recent) / L4 (prompt) tokens |
| **Naive vs shaped** | Full IDE transcript estimate vs synthesizer-shaped payload |
| **Cumulative cost** | Actual $ vs baseline (if all input were uncached) |
| **Trends** | Compression % and uncached tail % over turns |
| **Compaction timeline** | Dreaming v4 runs, ledger delta, trigger reason |
| **Recent table** | Per-request detail + recommendations |

Updates automatically via **Server-Sent Events** when Claude Code hits the proxy.

---

## Prerequisites

1. Proxy running (`systemctl --user status context-synthesizer-proxy`)
2. Claude Code routed through proxy (`ANTHROPIC_BASE_URL` in `~/.claude/settings.json`)
3. Use Claude Code in a project — dashboard populates on each API call

---

## Filters

- **Developer** — `TELEMETRY_DEVELOPER_ID` from setup
- **Session** — `X-Session-Id` header (Claude CLI session)

---

## Data sources

| Source | Path |
|--------|------|
| Live buffer | In-memory ring (last ~5000 events) |
| Persistent log | `context-synthesizer/stats/telemetry.jsonl` |

API:

- `GET /api/dashboard/data` — full snapshot JSON
- `GET /api/dashboard/stream` — SSE live feed

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Empty dashboard | Confirm proxy is active; use Claude Code through proxy |
| Wrong port | Match `PROXY_PORT` in `.env` (e.g. `8081` if Tabby uses 8080) |
| Old data only | Check `telemetry.jsonl` path; live SSE badge should show **live** |

See also [DEPLOY.md](DEPLOY.md) · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)
