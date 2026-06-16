This is to roll out the PoC for **Context Synthesizer**. It routes **Claude Code** through a local proxy so long sessions stay compact instead of growing unbounded context.

No git, no API key, no weekly manual work after setup.

### Get the package

1. Open SharePoint: [Context-Synthesizer](https://motadataindia-my.sharepoint.com/:f:/g/personal/harshil_shah_motadata_com/IgBhQlYbLSLgRa2PO0LB8JoNAUkR135NoV-Nc2ssPJnwgmM?e=LvMdib)
2. Sync in OneDrive → `OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.16`

### Install

```bash
cd "$HOME/OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.16"
bash run-setup.sh firstname.lastname
```

Example: `bash run-setup.sh harshil.shah` (Azure email local-part)

### Verify

```bash
systemctl --user status context-synthesizer-proxy
```

Open **live dashboard**: http://127.0.0.1:8080/dashboard (or :8081 if Tabby uses 8080)

Use Claude Code — charts update per turn (billing split, L1–L4 layers, naive vs shaped savings).

### If proxy fails

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
bash context-synthesizer/scripts/check_proxy_ready.sh
```

Full docs in package: `INSTALL.txt`, `docs/guides/DASHBOARD.md`

Thanks,  
Harshil
