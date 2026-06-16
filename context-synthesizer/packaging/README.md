# packaging/

| Path | Status |
|------|--------|
| **`build-release-tarball.sh`** | **Current** — bundle for shared drive (no git for developers) |
| `build-deb.sh`, `DEBIAN/`, `*.service` | Legacy `.deb` — unmaintained |
| `UBUNTU_INSTALL.md` | Historical |

**Developer delivery:** `run-setup.sh` in the package — live compaction + **`/dashboard`** on by default — or root [`install.sh`](../../install.sh).

```bash
bash context-synthesizer/packaging/build-release-tarball.sh
# → packaging/build/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
# → upload extracted folder to SharePoint (replace previous toolkit)
```

See [DEPLOY.md](../../docs/guides/DEPLOY.md) · [DEVELOPER_ONBOARDING.md](../../docs/guides/DEVELOPER_ONBOARDING.md) · [DASHBOARD.md](../../docs/guides/DASHBOARD.md) · [TEAM_ANNOUNCEMENT.md](../../docs/guides/TEAM_ANNOUNCEMENT.md)
