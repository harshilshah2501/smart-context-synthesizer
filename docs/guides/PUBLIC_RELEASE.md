# Public release checklist

Use this before making the repo public, cutting a release, or accepting external contributions.

---

## Never commit (blockers)

| Item | Why | Status in repo |
|------|-----|----------------|
| **`.env`** | Secrets, developer IDs | `.gitignore` — verify `git ls-files .env` is empty |
| **`stats/`** | Session telemetry, corpora | `context-synthesizer/stats/**` gitignored |
| **`stats/backups/`** | Colleagues' Claude memory exports | Must stay local only — delete before any `git add -A` |
| **`*.json` in stats/** | Hot-session analysis with personal data | Covered by `stats/.gitignore` (`*` ignore all) |
| **`packaging/share.conf`** | Org-specific OneDrive paths | Gitignored — use `share.conf.example` |
| **Session zip exports** | Raw Claude project backups | Never add to repo |

### Verify before push

```bash
git status
git ls-files | rg -i '\.env$|stats/|share\.conf|backup|\.zip'
# should return nothing sensitive
```

If `.env` was ever committed: `git rm --cached .env` and rotate any exposed keys.

---

## Generalize before sharing (should-fix)

| Item | Action |
|------|--------|
| **README / docs** | Primary install path = GitHub / tarball, not internal SharePoint |
| **`packaging/publish-to-sharepoint.sh`** | Optional enterprise helper; requires local `share.conf` |
| **`COPILOT_TOKEN` / Copilot backend** | Disabled unless `ENABLE_COPILOT_BACKEND=1`; may violate GitHub ToS |
| **`Claude.production.md`** | Large benchmark Layer-1 doc; review for internal product names before publish |
| **Corpus reports** | `docs/reports/*` use anonymized developer handles from private study — no raw session data |

---

## Already in good shape

- Core proxy, compaction, telemetry, dashboard code
- `.env.example` as single env template (includes developer config keys)
- `requirements.txt` minimal and pinned
- `proxy_message_bridge.py` tool-faithful assembly
- Unit tests for message bridge

---

## Optional enterprise deployment (not required for public users)

Teams can add locally (not in git):

```bash
cp packaging/share.conf.example packaging/share.conf
# edit OneDrive / shared-drive paths
bash packaging/publish-to-sharepoint.sh
```

See [DEPLOY.md](DEPLOY.md) § Optional: shared-drive publish.

---

## Fork / contributor hygiene

1. Copy `.env.example` → `.env` — never commit `.env`
2. Run proxy: `csynth doctor`
3. Keep all session data under `stats/` (gitignored)
4. Do not enable `ENABLE_COPILOT_BACKEND` unless you accept ToS risk

---

## Assessment summary (community review)

**Worth sharing:** Yes — layered compaction + cache-aligned proxy is novel and useful to the Claude Code community.

**Blockers addressed in this repo:**

1. `.env` gitignored, not tracked  
2. `stats/backups/` never in git — harden local `.gitignore`  
3. `stats/**` fully gitignored including JSON  
4. README/docs generalized for GitHub-first install  
5. `share.conf` replaced by `share.conf.example`  
6. Copilot backend gated + documented as unsupported  

**Maintainer action on local machines:** Delete or never add `stats/backups/`, `stats/*.json`, and `.env` before `git add`.
