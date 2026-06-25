# Project Engineering Context (Layer 1)

This file is pinned at **messages[0]** with `cache_control: ephemeral`. Keep it
**byte-stable** across requests — no timestamps, UUIDs, or session counters here.
Session state lives in the `X-Session-Id` header, not in this file.

Replace the template sections below with your project's real architecture. Aim for
**≥1,500 tokens** so Anthropic's prompt cache engages from turn 1. Verify with:

```bash
python3 count_tokens.py
```

---

## Project identity (customize)

| Field | Value |
|-------|-------|
| **Product** | _Your product name_ |
| **Repository** | _github.com/org/repo_ |
| **Primary language** | _e.g. Python 3.12, TypeScript 5.x_ |
| **Runtime** | _e.g. Linux / WSL2, FastAPI, React_ |
| **Owners** | _team or domain_ |

**Mission (one paragraph):** Describe what the system does, who uses it, and the
non-negotiable quality bar (latency, correctness, security, cost).

---

## Architecture (customize)

Document the stable shape of the system — not today's task list.

### Core components

| Component | Responsibility | Key paths |
|-----------|----------------|-----------|
| _API gateway_ | _HTTP entry, auth_ | _src/api/_ |
| _Domain logic_ | _Business rules_ | _src/core/_ |
| _Data layer_ | _Persistence, queries_ | _src/db/_ |
| _UI / CLI_ | _User interaction_ | _src/ui/_ |

### Data flow

1. Request enters through _edge/API_.
2. AuthN/AuthZ applied before handler logic.
3. Domain services own invariants; controllers stay thin.
4. Persistence through explicit repositories — no ORM calls scattered in handlers.
5. Side effects (email, queues) via async workers, not request thread.

### Boundaries

- **Do not** bypass the service layer from HTTP handlers.
- **Do not** import UI code into domain modules.
- **Prefer** dependency injection over global singletons.
- **Prefer** explicit types and schemas at module boundaries.

---

## Context Synthesizer integration

This session runs through a **local compaction proxy**. The proxy assembles:

| Layer | Content | Cached |
|-------|---------|--------|
| L1 | This file | Yes |
| L2 | History ledger (compacted state) | Yes |
| L3 | Recent turns (sliding window) | No |
| L4 | Current user prompt | No |

### Pinned checkpoints

When a decision must survive compaction, pin it in a user message:

```
@synth-remember: React 19 only — no ReactDOM.render; use createRoot.
```

Aliases: `@remember:`, `@pin:`, `@must-remember:`

Pinned facts are stored separately (L2a) and are not dropped by background compaction.

### Tool-heavy sessions

Active `tool_use` / `tool_result` loops pass through verbatim. Do not summarize
tool output in prose when the tool already returned structured data — reference paths
and outcomes instead of pasting full file bodies repeatedly.

---

## Code standards

### General

- **Minimal diffs** — change only what the task requires.
- **Match existing style** — naming, imports, error types, test patterns.
- **No drive-by refactors** unless explicitly requested.
- **Read before write** — inspect surrounding code and tests before editing.
- **One logical change per commit** when the user will commit your work.

### Python (if applicable)

- Python 3.12+, type hints on public functions.
- `async` for I/O-bound proxy and API code; avoid blocking calls in async paths.
- Prefer stdlib + project deps; no new packages without justification.
- Docstrings only for non-obvious business logic.

### TypeScript / JavaScript (if applicable)

- Strict TypeScript where the repo uses it.
- Prefer named exports; avoid default-export churn.
- Co-locate tests with features or follow repo `__tests__` convention.

### Error handling

- Fail fast with actionable messages — include _what failed_ and _how to fix_.
- Never swallow exceptions without logging context.
- User-facing errors: no stack traces; logs: full detail.

---

## Testing

- Run the **smallest relevant test set** before declaring done.
- Add tests for bug fixes (regression) and new public APIs.
- Do not add tests that only assert mocks or trivial getters.
- Prefer table-driven tests for parsing and compaction logic.

Common commands (adjust to repo):

```bash
pytest path/to/test_module.py -q
npm test -- --runInBand
```

---

## Security

- Never log secrets, tokens, or PII.
- Never commit `.env`, credentials, or session exports.
- Validate and sanitize external input at trust boundaries.
- Use parameterized queries — no string-built SQL.
- Prefer least-privilege API keys and scoped tokens.

---

## Git and review

- Commit messages: imperative mood, explain _why_ in one line when non-obvious.
- Do not amend or force-push unless the user explicitly asks.
- PR descriptions: what changed, how to test, risks.

---

## API and integration conventions

- REST: consistent resource naming, explicit HTTP status codes, idempotent PUT/PATCH.
- Version external APIs; document breaking changes.
- Timeouts and retries on all outbound HTTP — exponential backoff, capped attempts.
- Idempotency keys for payment-like or side-effecting operations.

---

## Performance and cost

- Prefer prompt-cache-friendly stable prefixes (this file + ledger).
- Avoid re-reading unchanged large files — cite prior conclusions.
- Batch related tool calls when the platform allows.
- For LLM work: smaller targeted prompts beat dumping entire repositories.

---

## Documentation

- Update README or module docs when behavior changes.
- Architecture decisions: short ADR or comment in PR — not buried in chat only.
- Link to canonical docs paths; avoid duplicating large specs in chat.

---

## Domain glossary (customize)

| Term | Definition |
|------|------------|
| _Ledger_ | Compacted session history (L2) |
| _Turn_ | One user message + assistant response pair |
| _…_ | _Add project-specific terms_ |

---

## Active constraints (customize)

List rules that override defaults for this codebase:

1. _e.g. All DB migrations must be backward-compatible for one release._
2. _e.g. Feature flags required for user-visible behavior changes._
3. _e.g. No direct production deploys — CI only._

---

## Deprecated patterns (customize)

| Deprecated | Use instead | Notes |
|------------|-------------|-------|
| _old pattern_ | _new pattern_ | _migration deadline if any_ |

---

## Reference links (customize)

- Architecture overview: _docs/architecture.md_
- Runbook / onboarding: _docs/onboarding.md_
- API spec: _docs/api/openapi.yaml_

---

_End of Layer 1 template. Expand sections with real project detail; re-run
`count_tokens.py` until **Cache Eligible: YES** (≥1,024 tokens)._
