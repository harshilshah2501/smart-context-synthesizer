# Testing the proxy with Cursor IDE

Use this guide to validate the synthesizer proxy on your own machine using
Cursor before rolling out to the wider team on Claude Code.

## What this tests

- The proxy receives requests, builds the layered payload (L1 Claude.md +
  L2 ledger + L3 rolling turns), and forwards to Anthropic.
- Telemetry appears in the live dashboard in real time.
- Compaction triggers after 10 turns, Dreaming v4 runs, and the ledger
  updates.
- The `@synth-remember:` checkpoint system pins facts across compactions.

---

## Prerequisites

```bash
# Proxy must be running
systemctl --user status context-synthesizer-proxy

# If not running, start it
systemctl --user start context-synthesizer-proxy

# Confirm it responds
curl -s http://127.0.0.1:8080/health
# → {"status":"ok","service":"context-synthesizer"}

# Confirm the OpenAI-compat models list works
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool | head -10
```

---

## Cursor setup — add a custom model

1. Open **Cursor Settings** (`Cmd/Ctrl+,`) → **Models** tab.
2. Scroll to **"OpenAI API Key"** (or **"+ Add Model"** depending on your
   Cursor version) and enter your **Anthropic API key** as the key value.
3. Set the **Base URL** to:
   ```
   http://127.0.0.1:8080
   ```
4. Add a model named exactly:
   ```
   claude-sonnet-4-6
   ```
   (must match an ID from `/v1/models` above)
5. Save. In the Cursor model picker (bottom-right of chat), select
   `claude-sonnet-4-6`.

> **WSL note:** Cursor runs on Windows; the proxy runs in WSL. Use the WSL IP
> instead of `127.0.0.1`:
> ```bash
> bash context-synthesizer/scripts/open_dashboard.sh  # shows the WSL IP
> ```
> Set the Base URL to `http://<WSL-IP>:8080`.

---

## Verify it's working

Open the dashboard in your browser:
```bash
bash context-synthesizer/scripts/open_dashboard.sh
```

Then send a message in Cursor chat. Within a second you should see:
- **Proxy requests** counter increment in the KPI cards.
- **Billing bifurcation** chart update with cache-read / uncached bars.
- The footer shows `updated HH:MM:SS`.

If you see the **"No proxy requests recorded yet"** amber banner, the request
did not reach the proxy. Check:
```bash
journalctl --user -u context-synthesizer-proxy -n 20 --no-pager
```
Look for a line like:
```
[PROXY] ⚠ ANTHROPIC_BASE_URL not set in ~/.claude/settings.json
```
(Cursor uses the Base URL in its own settings, so this warning is expected and
harmless for the Cursor test.)

---

## Checkpoint test

In a Cursor chat message, type:
```
@synth-remember: migrated http client from requests to httpx — all async
```
The proxy strips that line before forwarding, stores it as a pin, and includes
it in the L2a cached block on every subsequent turn.

Check the dashboard **"Active pinned checkpoints"** panel — your pin should
appear with its turn number.

After 10 turns, compaction runs in the background. Open the **Compaction
events** table and confirm the **Pins** column shows `📌 1`.

---

## Interpreting the telemetry

| KPI | What to look for |
|-----|-----------------|
| Cache read share | Should climb toward 60–80 % after L1 warms (turn 2+) |
| Compression vs naive | Should be 40–60 % smaller than full IDE history |
| IDE bloat ratio | How many messages Cursor sends vs what the proxy shapes to |
| Active pins | Increments each time you use `@synth-remember:` |

---

## Switching back to default Cursor models

Remove the custom Base URL in Cursor Settings → Models, or switch the model
picker back to a built-in model. The proxy continues running and can be used
again at any time.
