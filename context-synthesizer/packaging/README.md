# packaging/

| Path | Purpose |
|------|---------|
| **`build-release-tarball.sh`** | Bundle for release (no git for end users) |
| `run-setup.sh` | Developer entry point inside the shipped package |
| `INSTALL.txt` | Quick-ref copied into each toolkit folder |

**Developer delivery:** `bash run-setup.sh firstname.lastname` — live compaction + dashboard on by default — or root [`install.sh`](../../install.sh).

```bash
bash context-synthesizer/packaging/build-release-tarball.sh
# → packaging/build/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz
```

Build refuses to run if `context-synthesizer/.env` contains `ANTHROPIC_API_KEY`.

See [RELEASE.md](../../docs/guides/RELEASE.md) · [DEVELOPER_ONBOARDING.md](../../docs/guides/DEVELOPER_ONBOARDING.md) · [DASHBOARD.md](../../docs/guides/DASHBOARD.md)
