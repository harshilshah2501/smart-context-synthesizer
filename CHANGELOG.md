# Changelog

All notable changes to the public **Context Synthesizer** repository are documented here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, GitHub issue/PR templates
- README sections: project status (beta), limitations, privacy & security
- CI `compileall` step for bytecode sanity checks

### Changed

- GitHub Copilot backend moved to `context-synthesizer/experimental/` — not loaded by the supported proxy
- Cursor/OpenAI path limitations documented in README and `docs/guides/CURSOR_TEST.md`

## [0.1.0] - 2026-06-24

### Added

- Local FastAPI proxy for Claude Code and Cursor (Anthropic `/v1/messages` + OpenAI shim)
- Four-layer context stack (L1 rules, L2a pins, L2b ledger, L3 recent turns)
- Dreaming v4 code-aware compaction (Haiku background synthesis)
- Structured ledger validation with programmatic state override (`ledger_validation.py`)
- Tool-faithful message bridge (`proxy_message_bridge.py`)
- Live cost/cache dashboard and JSONL telemetry
- `@synth-remember:` pinned checkpoints
- `csynth` CLI (`doctor`, `dashboard`, `proxy on/off`, `upgrade`)
- Production `Claude.md` template above Anthropic cache floor
- GitHub Actions CI (unit tests)
- Install one-liner and release tarball

[Unreleased]: https://github.com/harshilshah2501/smart-context-synthesizer/compare/v0.1.0...main
[0.1.0]: https://github.com/harshilshah2501/smart-context-synthesizer/releases/tag/v0.1.0
