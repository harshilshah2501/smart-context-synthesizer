# Documentation cheatsheet

One-page map: **which doc to open**, **which command to run**.

---

## Start here

| I want to… | Read first | Then |
|------------|------------|------|
| **Install & use the proxy** | [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) | [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) · [DASHBOARD.md](DASHBOARD.md) |
| **Understand cost metrics** | [COST_SAVINGS.md](COST_SAVINGS.md) | [DASHBOARD.md](DASHBOARD.md) |
| **Test with Cursor** | [CURSOR_TEST.md](CURSOR_TEST.md) | [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) |
| **Ship a tarball** | [RELEASE.md](RELEASE.md) | [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) |
| **Architecture deep dive** | [context_os_technical_report.md](../context_os_technical_report.md) | — |

---

## Guides — quick pick

| Doc | One line |
|-----|----------|
| [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) | Install from git or tarball, WSL notes, smoke test |
| [CSYNTH_QUICK_REFERENCE.md](CSYNTH_QUICK_REFERENCE.md) | `csynth` — install, reinstall, proxy on/off, logs |
| [DASHBOARD.md](DASHBOARD.md) | Live cost/token dashboard, WSL browser URLs |
| [COST_SAVINGS.md](COST_SAVINGS.md) | Why **cost** drops when **payload** looks flat |
| [CURSOR_TEST.md](CURSOR_TEST.md) | Cursor IDE + OpenAI shim testing |
| [RELEASE.md](RELEASE.md) | Build `context-synthesizer-toolkit-*.tar.gz` |

---

## Command cheatsheet

### Install & daily use

```bash
# From git (public branch)
git clone -b public https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
bash install.sh firstname.lastname

# From tarball
tar -xzf context-synthesizer-toolkit-*.tar.gz
cd context-synthesizer-toolkit-*
bash run-setup.sh firstname.lastname

# Reinstall / upgrade
bash install.sh firstname.lastname --reinstall

# Proxy
csynth proxy on
csynth proxy off
csynth restart

# Status & debug
csynth status
csynth doctor
csynth dashboard
csynth logs
```

### Build release tarball

```bash
cd context-synthesizer
bash packaging/build-release-tarball.sh
```

---

## FAQ

| Question | Answer |
|----------|--------|
| Do I need an API key? | No — Claude Code Max/Pro forwards auth |
| Where is telemetry stored? | `context-synthesizer/stats/` (gitignored, local only) |
| Proxy not receiving traffic? | `csynth doctor` · [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) § smoke test |
| Dashboard empty in Windows browser? | Use WSL IP from `open_dashboard.sh`, not `127.0.0.1` |
