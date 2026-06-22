# packaging/

| Path | Purpose |
|------|---------|
| **`build-release-tarball.sh`** | Bundle for SharePoint / shared drive (no git for developers) |
| `run-setup.sh` | Developer entry point inside the shipped package |
| `INSTALL.txt` | Quick-ref copied into each toolkit folder |
| `team.conf.example` | Team lead template (`SYNC_DIR`, `ENABLE_PROXY`) |

**Developer delivery:** `bash run-setup.sh firstname.lastname` — live compaction + dashboard on by default — or root [`install.sh`](../../install.sh).

```bash
bash context-synthesizer/packaging/build-release-tarball.sh
# → packaging/build/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
# upload extracted folder to SharePoint (replace previous toolkit)
```

Build refuses to run if `context-synthesizer/.env` contains `ANTHROPIC_API_KEY` (Max/Pro teams ship without team keys).

See [DEPLOY.md](../../docs/guides/DEPLOY.md) · [DEVELOPER_ONBOARDING.md](../../docs/guides/DEVELOPER_ONBOARDING.md) · [DASHBOARD.md](../../docs/guides/DASHBOARD.md) · [TEAM_ANNOUNCEMENT.md](../../docs/guides/TEAM_ANNOUNCEMENT.md)
