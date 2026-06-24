# `csynth` quick reference

One CLI for install verification, proxy control, dashboard, and logs. Installed to `~/.local/bin/csynth` during setup.

**Requires:** `~/.local/bin` on your `PATH` (setup prints a hint if missing).

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Install & reinstall

### First install (from git)

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh firstname.lastname
```

### First install (from tarball)

```bash
tar -xzf context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
cd context-synthesizer-toolkit-YYYY.MM.DD
bash run-setup.sh firstname.lastname
```

### Reinstall (same machine, fresh copy)

From a new toolkit folder:

```bash
bash install.sh firstname.lastname --reinstall
```

Or from inside the package:

```bash
bash run-setup.sh firstname.lastname
# with install.sh at package root:
bash install.sh firstname.lastname --reinstall
```

`--reinstall` removes `~/.local/share/context-synthesizer` first, then runs setup again.

### After reinstall

```bash
csynth doctor
csynth proxy on    # if proxy was off
```

---

## Proxy: enable, disable, restart

| Command | What it does |
|---------|----------------|
| `csynth proxy on` | Start proxy service + set Claude Code `ANTHROPIC_BASE_URL` → local proxy |
| `csynth proxy off` | Stop proxy service + remove proxy URL from Claude settings (direct Anthropic) |
| `csynth proxy` | Show proxy service + Claude routing status |
| `csynth restart` | Restart `context-synthesizer-proxy` user service |
| `csynth status` | `systemctl` status + routing snippet |

### Typical flows

**Use synthesizer (default after install):**

```bash
csynth proxy on
csynth doctor
```

**Bypass proxy (debug / compare behavior):**

```bash
csynth proxy off
# use Claude Code normally — direct API
csynth proxy on   # re-enable when done
```

**Proxy running but errors / after code update:**

```bash
csynth restart
csynth logs       # watch for [PROXY] ✗ upstream error
```

**WSL note:** if `systemctl --user restart` hangs, use:

```bash
systemctl --user kill context-synthesizer-proxy
systemctl --user start context-synthesizer-proxy
```

---

## All `csynth` commands

| Command | Purpose |
|---------|---------|
| `csynth status` | Proxy systemd status + routing check |
| `csynth proxy on` | Enable proxy routing |
| `csynth proxy off` | Disable proxy routing |
| `csynth proxy` | Proxy on/off summary |
| `csynth dashboard` | Print (and optionally open) live dashboard URL |
| `csynth doctor` | Full preflight: service, port, Claude settings, health |
| `csynth logs` | Tail proxy journal (`journalctl -f`) |
| `csynth restart` | Restart proxy service |
| `csynth help` | Short usage |

### Dashboard

```bash
csynth dashboard          # print URLs (WSL IP + token on WSL)
csynth dashboard --open   # open in Windows browser (WSL)
```

On **WSL + Windows browser**, use the **WSL IP** URL printed — not `127.0.0.1` in Chrome. See [DASHBOARD.md](DASHBOARD.md).

---

## Verify after install

```bash
csynth status
csynth doctor
csynth dashboard
```

Send one message in Claude Code — dashboard KPIs should update. In logs:

```bash
csynth logs
# expect: [PROXY] → POST /v1/messages
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `csynth: command not found` | `export PATH="$HOME/.local/bin:$PATH"` |
| Proxy 502 / upstream errors | `csynth logs` — then `csynth restart` |
| Dashboard empty | `csynth proxy on` + use Claude through proxy |
| Port 8080 busy (Tabby, etc.) | Set `PROXY_PORT=8081` in `~/.local/share/context-synthesizer/context-synthesizer/.env`, then `bash …/configure_claude_proxy.sh` and `csynth restart` |
| Broken venv | `bash ~/.local/share/context-synthesizer/context-synthesizer/scripts/repair_venv.sh` then `csynth restart` |
| Compare cost vs payload | [COST_SAVINGS.md](COST_SAVINGS.md) |

---

## Install location

| Path | Contents |
|------|----------|
| `~/.local/share/context-synthesizer/` | Installed toolkit + venv |
| `~/.config/context-synthesizer/developer.env` | Developer ID, `ENABLE_PROXY` flag |
| `~/.claude/settings.json` | `ANTHROPIC_BASE_URL` when proxy on |

See [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) · [INSTALL.txt](../../INSTALL.txt) (in toolkit package root)
