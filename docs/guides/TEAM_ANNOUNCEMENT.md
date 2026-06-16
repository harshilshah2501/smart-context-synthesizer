# Team rollout message — Context Synthesizer

Copy-paste for Slack, Teams, or email. Update the SharePoint link and toolkit folder date (`context-synthesizer-toolkit-YYYY.MM.DD`) before sending.

---

**Subject:** Context Synthesizer — one-time setup (~5 min)

Hi team,

We’re rolling out the **Context Synthesizer** PoC. It routes **Claude Code** through a local proxy so long sessions stay compact instead of growing unbounded context.

**No git, no API key, no weekly manual work** after setup.

### Get the package

1. Open the SharePoint folder: [Context-Synthesizer](https://motadataindia-my.sharepoint.com/:f:/g/personal/harshil_shah_motadata_com/IgBhQlYbLSLgRa2PO0LB8JoNAUkR135NoV-Nc2ssPJnwgmM?e=LvMdib)
2. Click **Sync** in OneDrive so it appears locally, e.g.  
   `OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-YYYY.MM.DD`  
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
cd "$HOME/OneDrive - Motadata/ContextSynthesizer/context-synthesizer-toolkit-YYYY.MM.DD"
bash run-setup.sh harshil.shah
```

Setup takes ~5 minutes. It will:

- Create a local Python environment
- Start the **live compaction proxy** (background service)
- Point Claude Code at the proxy automatically
- Enable the **live dashboard** — `bash context-synthesizer/scripts/open_dashboard.sh`
- *(Optional)* Schedule Monday session summaries to SharePoint for team rollup

**You do not need a personal Anthropic API key** — Claude Code forwards your existing login.

### Verify it worked

```bash
systemctl --user status context-synthesizer-proxy
```

Status should be **active (running)**.

Open the **live dashboard**:

```bash
bash context-synthesizer/scripts/open_dashboard.sh
bash context-synthesizer/scripts/open_dashboard.sh --open   # opens Windows browser (WSL)
```

**WSL users:** use the **WSL IP** URL printed by the script (e.g. `http://172.22.x.x:8080/dashboard`).  
`127.0.0.1` in Windows Chrome often fails with `ERR_EMPTY_RESPONSE` (Tabby or separate Windows localhost).

*(Use port `8081` if setup printed `PROXY_PORT=8081`.)*

Use Claude Code in any project — the dashboard updates per turn with:

- Billing split (cache read / write / uncached tokens)
- Four-layer payload (L1 rules → L2 ledger → L3 recent → L4 prompt)
- **Naive IDE history vs shaped context** (where compaction saves size)
- Cumulative $ saved and compaction events

If the service won’t start:

```bash
journalctl --user -u context-synthesizer-proxy -n 40 --no-pager
bash context-synthesizer/scripts/check_proxy_ready.sh
```

**Port conflict:** see `docs/guides/DEPLOY.md` in the package (`PROXY_PORT=8081`).

### After setup

- **You:** use Claude Code as usual — compaction runs automatically; watch savings on `/dashboard`.
- **No weekly chores** unless you want SharePoint rollup reports.
- **More detail:** `INSTALL.txt`, `docs/guides/DEVELOPER_ONBOARDING.md`, `docs/guides/DASHBOARD.md`.

Reply in this thread if you hit issues (paste output from `check_proxy_ready.sh` or `journalctl`).

Thanks,  
Harshil

---

## Short version (quick ping)

> … Check proxy: `systemctl --user status context-synthesizer-proxy`. Dashboard: `bash context-synthesizer/scripts/open_dashboard.sh` (WSL IP for Windows browser). Details in `INSTALL.txt`.

---

## Team lead checklist

| Step | Action |
|------|--------|
| 1 | `bash context-synthesizer/packaging/build-release-tarball.sh` |
| 2 | Upload extracted folder (or `.tar.gz`) to SharePoint — replace previous toolkit |
| 3 | Edit `team.conf` in the package — set `SYNC_DIR` for your org |
| 4 | Send this message (update toolkit folder date in examples) |
| 5 | Weekly rollup: [DEPLOY.md](DEPLOY.md) |
| 6 | Optional: review team savings via each dev’s local `/dashboard` or weekly JSONL on SharePoint |
