# Team rollout message — Context Synthesizer

Copy-paste for Slack, Teams, or email. Update the SharePoint link and toolkit folder date before sending.

---

**Subject:** Context Synthesizer — one-time setup (~5 min)

Hi team,

We’re rolling out the **Context Synthesizer** PoC. It routes **Claude Code** through a local proxy so long sessions stay compact instead of growing unbounded context.

**No git, no API key, no weekly manual work** after setup.

### Get the package

1. Open the SharePoint folder: [Context-Synthesizer](https://motadataindia-my.sharepoint.com/:f:/g/personal/harshil_shah_motadata_com/IgBhQlYbLSLgRa2PO0LB8JoNAUkR135NoV-Nc2ssPJnwgmM?e=LvMdib)
2. Click **Sync** in OneDrive so it appears locally, e.g.  
   `OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.12`  
   *(Ubuntu without the Windows OneDrive app: download the `.tar.gz` from SharePoint and extract it.)*

### Prerequisites (once per machine)

- **Python 3** + venv — Ubuntu: `sudo apt install -y python3 python3-venv`
- **Claude Code** installed and logged in (Max/Pro as usual)
- **Linux or WSL** recommended (proxy + cron use systemd)

### Install (one command)

Open a terminal **inside the synced toolkit folder** and run:

```bash
bash run-setup.sh firstname.lastname
```

Use your **Azure email local-part** as the ID (e.g. `harshil.shah` for `harshil.shah@motadata.com`).

Example:

```bash
cd "$HOME/OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-2026.06.12"
bash run-setup.sh harshil.shah
```

Setup takes ~5 minutes. It will:

- Create a local Python environment
- Start the **live compaction proxy** (background service)
- Point Claude Code at the proxy automatically
- *(Optional)* Schedule Monday session summaries to SharePoint for team rollup

**You do not need a personal Anthropic API key** — Claude Code forwards your existing login.

### Verify it worked

```bash
systemctl --user status context-synthesizer-proxy
```

Status should be **active (running)**. Then use Claude Code normally in any project.

If the service won’t start:

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
bash context-synthesizer/scripts/check_proxy_ready.sh
```

**Port conflict:** if something else (e.g. Tabby) uses port 8080, use `PROXY_PORT=8081` — see `docs/guides/DEPLOY.md` in the package.

### After setup

- **You:** use Claude Code as usual — compaction runs automatically on long sessions.
- **No weekly chores** unless you want to check logs under `~/.local/state/context-synthesizer/`.
- **More detail:** `INSTALL.txt` and `docs/guides/DEVELOPER_ONBOARDING.md` in the same folder.

Reply in this thread if you hit issues (paste output from `check_proxy_ready.sh` or `journalctl`).

Thanks,  
Harshil

---

## Short version (quick ping)

> Context Synthesizer is on SharePoint: [link](https://motadataindia-my.sharepoint.com/:f:/g/personal/harshil_shah_motadata_com/IgBhQlYbLSLgRa2PO0LB8JoNAUkR135NoV-Nc2ssPJnwgmM?e=LvMdib) → Sync in OneDrive → `cd` into `context-synthesizer-toolkit-2026.06.12` → `bash run-setup.sh your.name` (Azure local-part, e.g. `harshil.shah`). ~5 min, no git/API key. Check: `systemctl --user status context-synthesizer-proxy`. Details in `INSTALL.txt`.

---

## Team lead checklist

| Step | Action |
|------|--------|
| 1 | `bash context-synthesizer/packaging/build-release-tarball.sh` |
| 2 | Upload extracted folder (or `.tar.gz`) to SharePoint |
| 3 | Edit `team.conf` in the package — set `SYNC_DIR` for your org |
| 4 | Send this message (update folder date in examples) |
| 5 | Weekly rollup: [DEPLOY.md](DEPLOY.md) |
