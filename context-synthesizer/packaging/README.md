# packaging/

| Path | Status |
|------|--------|
| **`build-release-tarball.sh`** | **Current** — bundle for shared drive (no git for developers) |
| `build-deb.sh`, `DEBIAN/`, `*.service` | Legacy `.deb` — unmaintained |
| `UBUNTU_INSTALL.md` | Historical |

**Developer delivery:** root [`install.sh`](../../install.sh) — curl or `--tarball-file` from drive.

```bash
bash context-synthesizer/packaging/build-release-tarball.sh
# → packaging/build/context-synthesizer-toolkit-*.tar.gz
```

See [DEPLOY.md](../../docs/guides/DEPLOY.md) · [DEVELOPER_ONBOARDING.md](../../docs/guides/DEVELOPER_ONBOARDING.md).
