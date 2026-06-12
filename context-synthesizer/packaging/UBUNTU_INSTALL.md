# Ubuntu Package Install — deprecated

> **This path was dropped.** Current install: `bash run-setup.sh` from the SharePoint toolkit package — live compaction via **systemd user service** (`context-synthesizer-proxy`). Offline corpus: [Usage.md](../../docs/guides/Usage.md) **Mode D**. No `.deb`.
>
> The files below remain for historical reference only.

---

# Ubuntu Package Install — Mode B (legacy)

Install the `.deb` once. Claude CLI traffic routes through the local proxy; **every successful `/v1/messages` call** appends one bifurcated telemetry line to JSONL.

---

## Build the package (team lead / CI)

```bash
cd ~/Out-of-bound-chronicles
chmod +x packaging/build-deb.sh
./packaging/build-deb.sh
# → packaging/build/context-synthesizer_0.1.0_all.deb
```

Distribute the `.deb` via internal apt repo, Slack, or shared drive.

---

## Developer install

```bash
sudo apt install ./context-synthesizer_0.1.0_all.deb
```

### 1. Start per-user proxy (Claude CLI BYOK — recommended)

```bash
context-synthesizer-setup-user
curl -s http://127.0.0.1:8080/health
```

### 2. Claude CLI settings

`~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8080",
    "ANTHROPIC_API_KEY": "sk-ant-api03-...",
    "TELEMETRY_DEVELOPER_ID": "alice"
  }
}
```

No `/etc/default` API key required — Claude CLI forwards `x-api-key` per request.

### 3. View your stats

```bash
tail -f ~/.local/share/context-synthesizer/stats/telemetry.jsonl
context-synthesizer-collect-stats --logs ~/.local/share/context-synthesizer/stats/
```

### Optional — shared system service

```bash
sudo nano /etc/default/context-synthesizer   # team ANTHROPIC_API_KEY
sudo systemctl enable --now context-synthesizer
sudo tail -f /var/lib/context-synthesizer/stats/telemetry.jsonl
```

---

## Does it collect for every request?

| Request | Telemetry JSONL? |
|---------|------------------|
| `POST /v1/messages` — success (sync) | **Yes** — full `usage` bifurcation + cost |
| `POST /v1/messages` — success (streaming) | **Yes** — after stream completes |
| `GET /health` | **No** — liveness probe only |
| Malformed body (400 from proxy) | **No** |
| Anthropic API error (502) | **No** |
| Background Haiku compaction calls | **No** — internal, not developer-facing |

**Mode B logs one line per successful Claude API exchange** that returns `usage` from Anthropic. That is every normal Claude CLI turn.

Each line includes:

- `cache_read_input_tokens`, `cache_creation_input_tokens`, `input_tokens`, `output_tokens`
- `actual_usd`, `baseline_usd`, `saved_usd`, `savings_pct`, `cache_efficiency_pct`
- `developer_id`, `session_id`, `model`, `client`, `turn_number`, `compaction_triggered`

Default log path: `/var/lib/context-synthesizer/stats/telemetry.jsonl`

---

## Replace production Claude.md

```bash
sudo cp /path/to/your/Claude.md /etc/context-synthesizer/Claude.md
sudo systemctl restart context-synthesizer
```

Verify token budget:

```bash
sudo -u context-synthesizer \
  /usr/lib/context-synthesizer/.venv/bin/python \
  /usr/lib/context-synthesizer/count_tokens.py \
  --path /etc/context-synthesizer/Claude.md
```

---

## Uninstall

```bash
sudo apt remove context-synthesizer
```

Stats under `/var/lib/context-synthesizer/` are preserved unless purged:

```bash
sudo apt purge context-synthesizer
```
