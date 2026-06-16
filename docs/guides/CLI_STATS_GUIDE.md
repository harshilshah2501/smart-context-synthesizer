# Mode A — Claude CLI Log Import

Import **native Claude Code session logs** for per-turn token bifurcation (`input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`).

Mode A writes `source: cli_import` (per assistant turn). For session-level compression
estimates and hot-session analysis, use **Mode D** (`source: claude_corpus`) or **Mode C**
(`source: cursor_import`). See [README § modes](../../context-synthesizer/README.md#data-collection-modes).

---

## Where logs live

```text
~/.claude/projects/<project-path>/<session-uuid>.jsonl
```

Each assistant turn includes a `usage` object with real token counts from Anthropic.

---

## Weekly export

```bash
cd ~/Out-of-bound-chronicles
export TELEMETRY_DEVELOPER_ID="alice"

.venv/bin/python context-synthesizer/import_cli_logs.py \
  --output context-synthesizer/stats/alice_cli.jsonl

# Optional: only recent data
.venv/bin/python context-synthesizer/import_cli_logs.py --since 2026-06-01
```

Send `stats/alice_cli.jsonl` to the team lead.

---

## JSONL event shape

```json
{
  "ts": "2026-06-10T15:04:00+00:00",
  "source": "cli_import",
  "developer_id": "alice",
  "session_id": "ac4ecef7-...",
  "usage": {
    "input_tokens": 6,
    "cache_read_input_tokens": 537417,
    "cache_creation_input_tokens": 0,
    "output_tokens": 1024
  },
  "cost": {
    "actual_usd": 0.16,
    "baseline_usd": 1.61,
    "saved_usd": 1.45,
    "savings_pct": 90.1
  }
}
```

---

## Team lead: aggregate

```bash
.venv/bin/python context-synthesizer/collect_stats.py \
  --logs context-synthesizer/stats/

.venv/bin/python context-synthesizer/collect_stats.py \
  --logs context-synthesizer/stats/ \
  --export context-synthesizer/stats/team_report.csv
```

---

## What to look for

| Signal | Healthy | Action if bad |
|--------|---------|---------------|
| `cache_read_input_tokens` share | High on warm turns | Native caching works; optimize history shape (synthesizer) |
| `input_tokens` per turn | Small uncached tail | History bloat — see Mode D compression estimates |
| Session length | — | Sessions 100+ turns → run `analyze_hot_session.py` |

---

## Environment reference

| Variable | Purpose |
|----------|---------|
| `TELEMETRY_DEVELOPER_ID` | Developer name on imported events |
| `CLAUDE_CLI_LOG_ROOT` | Override `~/.claude/projects` path |

---

See also: [Usage.md](Usage.md) · [SYNTHESIZER_RND_REPORT.md](../reports/SYNTHESIZER_RND_REPORT.md)
