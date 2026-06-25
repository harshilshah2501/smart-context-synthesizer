# Security Policy

Context Synthesizer is a **local developer tool** that sits between your IDE and the Anthropic API. It is not hardened for untrusted networks or multi-tenant deployment.

**Project status:** Beta — see [README.md](README.md#project-status).

## Supported use

- Run on your own machine (or WSL) with `PROXY_HOST=127.0.0.1` (default).
- Use Claude Code Max/Pro OAuth or your own Anthropic API key.
- Treat telemetry and pinned checkpoints as **local, potentially sensitive project data**.

## Reporting vulnerabilities

If you find a security issue, please **do not** open a public GitHub issue with exploit details.

Email or DM the maintainer via [GitHub profile](https://github.com/harshilshah2501) with:

- Description and impact
- Steps to reproduce
- Affected version / commit

We will acknowledge within a reasonable timeframe and coordinate a fix before public disclosure when appropriate.

## API keys and authentication

| Path | Behavior |
|------|----------|
| **Claude Code** | Forwards `x-api-key` or OAuth bearer token per request. The proxy does not persist keys beyond in-memory session state. |
| **Fallback** | `ANTHROPIC_API_KEY` in `.env` if the client sends no key. |
| **Storage** | `.env` is gitignored. Never commit API keys or `DASHBOARD_TOKEN`. |

The proxy forwards credentials to **Anthropic only** (supported product path). It does not send your keys to third parties.

## Dashboard exposure

The live dashboard (`/dashboard`, `/api/*`) shows session telemetry, costs, compaction events, and pinned checkpoint text.

| Setting | Effect |
|---------|--------|
| `PROXY_HOST=127.0.0.1` (default) | API and dashboard bind to loopback only. |
| `PROXY_HOST=0.0.0.0` | Binds on all interfaces — reachable from LAN/containers. |
| `DASHBOARD_TOKEN` | Requires `?token=` or `X-Dashboard-Token` header for dashboard routes when set. |
| `DASHBOARD_LOCALHOST_ONLY=1` | Blocks non-loopback clients from dashboard routes. |

**Recommendations:**

1. Keep `PROXY_HOST=127.0.0.1` unless you need remote access.
2. If binding wide (`0.0.0.0`), set `DASHBOARD_TOKEN` (WSL install may auto-generate one).
3. On shared dev boxes or cloud VMs, use `DASHBOARD_LOCALHOST_ONLY=1` or SSH tunnel to localhost.

The proxy prints a startup warning when `PROXY_HOST=0.0.0.0` without `DASHBOARD_TOKEN` or `DASHBOARD_LOCALHOST_ONLY`.

## Telemetry and privacy

| Artifact | Location | Contents |
|----------|----------|----------|
| `stats/telemetry.jsonl` | Install dir (gitignored) | Per-request usage, cost, session ID, developer ID, context sizes |
| Dashboard checkpoints API | In-memory + JSONL | Text from `@synth-remember:` pins |

Telemetry stays **on disk locally**. It is not uploaded by the proxy. You are responsible for backup, retention, and access control on that machine.

Do not commit `stats/`, `.env`, or `share.conf` — they are in `.gitignore`.

## Session data

Sessions (ledger, rolling turns, pins) are **in-memory only**. Restarting the proxy clears session state. There is no encryption at rest for in-memory data.

## Dependencies

Runtime dependencies use lower-bound versions in `context-synthesizer/requirements.txt`. Pin versions in production installs if you need reproducible builds.

## Out of scope (unsupported)

- Exposing the proxy on the public internet without additional auth/TLS
- Running as a shared multi-user service
- Experimental backends in `context-synthesizer/experimental/` — not part of the supported product
