This is to roll out the PoC for **Context Synthesizer**. It routes **Claude Code** through a local proxy so long sessions stay compact instead of growing unbounded context.

No git, no API key, no weekly manual work after setup.

### Get the package

1. Open SharePoint: [Context-Synthesizer](https://motadataindia-my.sharepoint.com/:f:/g/personal/harshil_shah_motadata_com/IgBhQlYbLSLgRa2PO0LB8JoNAUkR135NoV-Nc2ssPJnwgmM?e=LvMdib)
2. Sync in OneDrive → `OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.16`

*(Ubuntu without OneDrive: download the `.tar.gz` from SharePoint and extract.)*

### Prerequisites

- Python 3 + venv: `sudo apt install -y python3 python3-venv`
- Claude Code installed and logged in (Max/Pro)
- **WSL:** enable systemd once — add to `/etc/wsl.conf`: `[boot]` / `systemd=true`, then `wsl --shutdown` from Windows and reopen WSL

### Install

```bash
cd "$HOME/OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.16"
bash run-setup.sh firstname.lastname
```

Example: `bash run-setup.sh harshil.shah` (Azure email local-part)

### Verify

```bash
systemctl --user status context-synthesizer-proxy
bash context-synthesizer/scripts/check_proxy_ready.sh
bash context-synthesizer/scripts/open_dashboard.sh
bash context-synthesizer/scripts/open_dashboard.sh --open   # WSL → Windows browser
```

**WSL:** use the **WSL IP** URL from `open_dashboard.sh` (includes `?token=...`) — **not** `127.0.0.1` in Windows Chrome. Do not bookmark `/dashboard` without the token.

Use Claude Code — charts update per turn (billing split, L1–L4 layers, naive vs shaped savings).

### If proxy fails

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
bash context-synthesizer/scripts/check_proxy_ready.sh
```

**Port 8080 busy (Tabby):**

```bash
echo 'PROXY_PORT=8081' >> context-synthesizer/.env
bash context-synthesizer/scripts/configure_claude_proxy.sh
bash context-synthesizer/scripts/install_proxy_service.sh
```

Full docs: `INSTALL.txt`, `docs/guides/DEVELOPER_ONBOARDING.md`, `docs/guides/DASHBOARD.md`

Thanks,  
Harshil
