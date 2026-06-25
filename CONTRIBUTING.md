# Contributing

Thanks for your interest in Context Synthesizer. This public repository is **fully usable on its own** — you do not need access to the private internal repo to install, run, or contribute to the proxy.

## Project status

**Beta** — the core proxy, compaction, and dashboard work, but APIs and behavior may change between minor releases. See [CHANGELOG.md](CHANGELOG.md).

## Getting started

```bash
git clone https://github.com/harshilshah2501/smart-context-synthesizer.git
cd smart-context-synthesizer/context-synthesizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
pytest test_proxy_message_bridge.py test_compaction.py test_ledger_validation.py test_proxy_routes.py test_dashboard_api.py -q
```

Optional local proxy test:

```bash
# Terminal 1
uvicorn proxy_tool:app --host 127.0.0.1 --port 8080

# Terminal 2
python test_simulator.py --base-url http://127.0.0.1:8080 --turns 12
```

## What to contribute

Good first contributions:

- Unit or contract tests (especially FastAPI routes and dashboard auth)
- Documentation fixes and clearer limitations
- Bug fixes with a failing test
- Dashboard UX improvements

Please open an issue before large refactors or new features so we can align on design.

## Pull request guidelines

1. **Scope** — One logical change per PR when possible.
2. **Tests** — Add or update tests for behavior changes. Run:

   ```bash
   cd context-synthesizer
   pytest test_proxy_message_bridge.py test_compaction.py test_ledger_validation.py test_proxy_routes.py test_dashboard_api.py -q
   python -m compileall .
   ```
3. **Secrets** — Never commit `.env`, `stats/`, API keys, or local telemetry.
4. **Docs** — Update README or `docs/` when user-facing behavior changes.
5. **Style** — Match existing code: type hints, minimal comments, no drive-by refactors.

## Branches

- `main` on this repo is the **public OSS** release branch.
- Internal team tooling lives in a separate private repository and is not required for contributions here.

## Security

See [SECURITY.md](SECURITY.md) before reporting or fixing security-related issues.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
