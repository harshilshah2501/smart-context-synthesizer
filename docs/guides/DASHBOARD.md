# Live telemetry dashboard

Real-time bifurcation of **where the Context Synthesizer saves tokens and cost** — served by the same proxy process as Claude Code traffic.

**URL:** run `csynth dashboard` or `bash context-synthesizer/scripts/open_dashboard.sh` — prints WSL + Linux URLs. Default port `8080` (or `PROXY_PORT` in `context-synthesizer/.env`).

**WSL + Windows browser:** use the **WSL IP** URL from `open_dashboard.sh` — **never** `127.0.0.1` in Windows Chrome (`ERR_EMPTY_RESPONSE`).

**Required on WSL:** `PROXY_HOST=0.0.0.0` in `context-synthesizer/.env` so Windows can connect via WSL IP. New installs set this automatically; existing:

```bash
echo 'PROXY_HOST=0.0.0.0' >> context-synthesizer/.env
systemctl --user restart context-synthesizer-proxy
bash context-synthesizer/scripts/open_dashboard.sh --open
```

**Dashboard auth (WSL):** new WSL installs auto-generate `DASHBOARD_TOKEN` in `.env`. Always open the dashboard via `open_dashboard.sh` — URLs include `?token=...`. Do not share the token outside your machine.

**Native Linux (optional):** set `DASHBOARD_LOCALHOST_ONLY=1` to block non-loopback access without a token. See `context-synthesizer/.env.example`.

---

## What you see

| Section | Shows |
|---------|--------|
| **KPI cards** | Requests, compactions, $ saved, compression vs naive IDE history, cache read %, uncached tail %, IDE bloat ratio |
| **Cache-floor banner** | Amber warning when estimated L1+L2 prefix is below Anthropic's 1,024-token cache minimum |
| **Billing bifurcation** | Per turn: `cache_read` / `cache_write` / `uncached` tokens (Anthropic billing buckets) |
| **Four-layer payload** | Est. L1 (rules) / L2 (ledger) / L3 (recent) / L4 (prompt) tokens |
| **Naive vs shaped** | Full IDE transcript estimate vs synthesizer-shaped payload — see [COST_SAVINGS.md](COST_SAVINGS.md) |
| **Cumulative cost** | Actual $ vs baseline (if all input were uncached) |
| **Trends** | Compression % and uncached tail % over turns |
| **Compaction timeline** | Dreaming v4 runs, ledger delta, trigger reason |
| **Recent table** | Per-request detail + recommendations |

Updates automatically via **Server-Sent Events** when Claude Code hits the proxy.

---

## Prerequisites

1. Proxy running (`csynth status` or `systemctl --user status context-synthesizer-proxy`)
2. Claude Code routed through proxy (`csynth proxy on` or `ANTHROPIC_BASE_URL` in `~/.claude/settings.json`)
3. Use Claude Code in a project — dashboard populates on each API call

**Understanding the numbers:** [COST_SAVINGS.md](COST_SAVINGS.md) explains why **cost** can drop while **payload size** looks flat.

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
| **401 on dashboard** | Use URL from `open_dashboard.sh` (includes `?token=`). Token is in `context-synthesizer/.env` |
| Wrong port | Match `PROXY_PORT` in `.env` (e.g. `8081` if Tabby uses 8080) |
| Old data only | Check `telemetry.jsonl` path; live SSE badge should show **live** |
| **`ERR_EMPTY_RESPONSE` in Windows browser** (curl in WSL works) | See **WSL + Windows browser** below |

### WSL + Windows browser

On **WSL2**, `127.0.0.1` inside Linux is **not** the same as `127.0.0.1` in Chrome/Edge on Windows.  
Also **Tabby** (or another Windows app) may own port **8080 on Windows** while the synthesizer proxy runs on **8080 inside WSL** — `curl` in WSL works; Windows browser gets an empty response.

**Fix — use the WSL IP in your Windows browser:**

```bash
# In WSL (toolkit folder)
hostname -I | awk '{print $1}'
# Example output: 172.22.123.45

# Open in Windows browser:
#   http://172.22.123.45:8080/dashboard
# (use your PROXY_PORT if not 8080)
```

One-liner to open from WSL:

```bash
bash context-synthesizer/scripts/open_dashboard.sh --open
```

**Windows 11 (mirrored networking):** `localhost` from Windows may forward to WSL — if it still fails, use the WSL IP above.

**Alternative:** use a dedicated port on WSL only (e.g. `PROXY_PORT=8081`) and always browse via `http://<WSL_IP>:8081/dashboard`.

See also [COST_SAVINGS.md](COST_SAVINGS.md) · [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)
