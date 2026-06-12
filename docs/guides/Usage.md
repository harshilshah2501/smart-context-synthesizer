# Context Synthesizer — Developer Setup Guide

**Team rollout:** see **[DEPLOY.md](DEPLOY.md)** for one-time setup, weekly export scripts, and team-lead rollup.

## Modes at a glance

All modes are **offline** — import session logs from disk. No API key, no proxy, no install.

| Mode | Who | Tool | Data path |
|------|-----|------|-----------|
| **A** | Default — Claude Code | `import_cli_logs.py` | `~/.claude/projects/<project>/<session>.jsonl` |
| **C** | Cursor IDE | `import_cursor_sessions.py` | `~/.cursor/projects/.../agent-transcripts/` |
| **D** | Claude Max / Pro | `import_claude_sessions.py` | `~/.claude/projects/<project>/<session>.jsonl` |

| | Mode A | Mode D |
|--|--------|--------|
| Import depth | Per-assistant-turn `usage` | Full session analysis + synthesizer counterfactual |
| Best for | Quick weekly token snapshot | Synthesizer R&D, hot sessions, team corpus |

Full comparison: [README § Data collection modes](../../context-synthesizer/README.md#data-collection-modes).

---

## Mode A — Default (Claude Code)

Claude Code stores every session locally. Mode A imports assistant turns with real token `usage`.

```bash
cd ~/Out-of-bound-chronicles
export TELEMETRY_DEVELOPER_ID="your-github-handle"

.venv/bin/python context-synthesizer/import_cli_logs.py \
  --output context-synthesizer/stats/$(whoami)_cli.jsonl

# Optional: only recent sessions
.venv/bin/python context-synthesizer/import_cli_logs.py --since 2026-06-01
```

Send `stats/*_cli.jsonl` to your team lead. See [CLI_STATS_GUIDE.md](guides/CLI_STATS_GUIDE.md) for field details.

---

## Mode D — Claude Max / Pro (recommended for synthesizer R&D)

Same log paths as Mode A, but richer analysis: turn growth, file re-reads, compression estimates, cache read %.

```bash
.venv/bin/python context-synthesizer/import_claude_sessions.py \
  --developer your-github-handle \
  --min-turns 25 \
  --export stats/$(whoami)_claude.csv
```

### Deep-dive one long session

```bash
.venv/bin/python context-synthesizer/analyze_hot_session.py \
  --source claude --largest --export stats/hot_session.json
```

### Filter by project

```bash
.venv/bin/python context-synthesizer/import_claude_sessions.py --project my-repo-name
.venv/bin/python context-synthesizer/analyze_hot_session.py --source claude --project my-repo --largest
```

---

## Mode C — Cursor IDE

```bash
.venv/bin/python context-synthesizer/import_cursor_sessions.py --project m-coder --min-turns 25
.venv/bin/python context-synthesizer/analyze_hot_session.py --source cursor --project m-coder --largest
```

Cursor logs lack per-turn API `usage` — analysis uses char-based estimates. Claude Mode D is richer for token bifurcation.

---

## Team lead: aggregate corpus

Collect corpus files from developers (default output paths):

| Mode | Default file | JSONL `source` tag |
|------|--------------|-------------------|
| A | `stats/telemetry.jsonl` (or custom `--output`) | `cli_import` |
| D | `stats/claude_corpus.jsonl` | `claude_corpus` |
| C | `stats/cursor_corpus.jsonl` | `cursor_import` |

```bash
.venv/bin/python context-synthesizer/collect_stats.py \
  --logs context-synthesizer/stats/ \
  --group-by developer_id \
  --export stats/team_report.csv
```

Use `--source claude_corpus` to filter Mode D only. For compression deep-dives, prefer `analyze_hot_session.py`.

---

## What each mode provides

| Mode | API key? | Token bifurcation | Session shape | Synthesizer counterfactual |
|------|----------|-------------------|---------------|--------------------------|
| **A** | No | Yes (assistant turns) | Limited | No |
| **D** | No | Yes (full session) | Yes | Yes |
| **C** | No | Estimates only | Yes | Yes (char-based) |

---

## Building the smart synthesizer from corpus data

1. **Collect** long sessions (`--min-turns 25`) — Mode D or C
2. **Analyze** hot sessions — file re-reads, growth spikes, tool loops
3. **Tune** compaction prompts and thresholds in `compaction.py` / `proxy_tool.py`
4. **Validate** compression estimates against new weekly exports

Target signals:
- Files read 10+ times → ledger should hold latest snippet only
- Naive context >> synth estimate → synthesizer has high value
- Low `cache_read` % in Claude logs → production `Claude.md` sizing (gateway target)

---

## Troubleshooting

### `~/.claude/projects` not found

Run Claude Code in at least one project directory first.

### No token usage in import

Older CLI versions may omit `usage` on some lines — upgrade Claude Code.

---

## Further reading

| Doc | Contents |
|-----|----------|
| [CLI_STATS_GUIDE.md](guides/CLI_STATS_GUIDE.md) | Mode A import details |
| [SYNTHESIZER_RND_REPORT.md](reports/SYNTHESIZER_RND_REPORT.md) | Corpus findings + roadmap |
| [README.md](../../context-synthesizer/README.md) | Architecture overview |
