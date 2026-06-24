# Developer onboarding

**Time:** ~5 minutes once. After setup: use Claude Code normally.

**Quick CLI:** [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · **Cost metrics:** [COST_SAVINGS.md](COST_SAVINGS.md)

---

## Install

### From git (`public` branch)

```bash
git clone -b public https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh your.handle
```

### One-liner (no clone)

```bash
curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/public/install.sh | bash -s -- your.handle
```

### From release tarball

```bash
tar -xzf context-synthesizer-toolkit-*.tar.gz
cd context-synthesizer-toolkit-*
bash run-setup.sh your.handle
```

Use a short developer id (e.g. email local-part: `jane.doe`).

**Live compaction (default ON):** Claude Code routes through a local proxy; Dreaming v4 compacts context during long sessions. Max/Pro login forwards auth — no API key at setup.

```bash
export PATH="$HOME/.local/bin:$PATH"
csynth doctor && csynth dashboard
```

**Proxy toggle:**

```bash
csynth proxy on | off | restart
```

---

## WSL + dashboard

Proxy and Claude Code run **inside WSL**. The live dashboard is served from WSL too.

**WSL systemd (once):** `/etc/wsl.conf` → `[boot]` / `systemd=true`, then `wsl --shutdown` from Windows and reopen WSL. Required for the proxy user service.

| Where | URL |
|-------|-----|
| **WSL terminal** | From `open_dashboard.sh` — `http://127.0.0.1:<PROXY_PORT>/dashboard?token=...` |
| **Windows Chrome/Edge** | From `open_dashboard.sh` — `http://<WSL_IP>:<PROXY_PORT>/dashboard?token=...` |

WSL setup auto-generates **`DASHBOARD_TOKEN`** in `context-synthesizer/.env`. Always use URLs from `open_dashboard.sh`.

```bash
bash context-synthesizer/scripts/open_dashboard.sh
bash context-synthesizer/scripts/open_dashboard.sh --open
```

---

## Ubuntu Linux (native)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
cd smart-context-synthesizer/context-synthesizer
bash install.sh your.handle
```

---

## What you get

| After setup | You do | Benefit |
|-------------|--------|---------|
| Live proxy ON | Use Claude Code normally | Context compaction during sessions |
| `/dashboard` | `csynth dashboard` while coding | Cache/cost/layers per request |
| `csynth` on PATH | `csynth doctor`, `csynth logs` | Status, proxy toggle, troubleshooting |

---

## `csynth` commands

| Command | Purpose |
|---------|---------|
| `csynth status` | Proxy service + routing |
| `csynth proxy on` / `off` | Enable / disable synthesizer |
| `csynth dashboard` | Live cost & token dashboard URL |
| `csynth doctor` | Full routing preflight |
| `csynth logs` | Tail proxy journal |
| `csynth restart` | Restart proxy service |

**Reinstall:** `bash install.sh your.handle --reinstall`

Full reference: [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md)

---

## Prerequisites

| Item | Notes |
|------|-------|
| `python3`, `curl`, `tar` | Linux / macOS / WSL |
| Claude Code | Normal CLI use |
| Browser | WSL IP in Windows browser; see `open_dashboard.sh` |

### Smoke test

```bash
csynth status
csynth doctor
csynth dashboard
```

```bash
systemctl --user status context-synthesizer-proxy
bash context-synthesizer/scripts/check_proxy_ready.sh
bash context-synthesizer/scripts/open_dashboard.sh
bash context-synthesizer/scripts/verify_claude_routing.sh
```

**WSL + Claude Code on Windows:** setup configures WSL `~/.claude/settings.json`, Windows `%USERPROFILE%\.claude\settings.json`, and VS Code `claudeCode.environmentVariables`. Restart VS Code after re-running configure.

If the service won't start:

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
```

**Broken venv (`anyio._backends`):**

```bash
bash context-synthesizer/scripts/repair_venv.sh
csynth restart
```

**Port conflict (8080 busy):**

```bash
echo 'PROXY_PORT=8081' >> context-synthesizer/.env
bash context-synthesizer/scripts/configure_claude_proxy.sh
bash context-synthesizer/scripts/install_proxy_service.sh
```
