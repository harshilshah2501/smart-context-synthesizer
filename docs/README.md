# Documentation

All project documentation lives here (single `docs/` tree).

**Cheatsheet:** [guides/DOCS_CHEATSHEET.md](guides/DOCS_CHEATSHEET.md) · **Public release:** [guides/PUBLIC_RELEASE.md](guides/PUBLIC_RELEASE.md)

## Guides (how to run)

| Doc                                                    | Purpose                              |
| ------------------------------------------------------ | ------------------------------------ |
| [guides/PUBLIC_RELEASE.md](guides/PUBLIC_RELEASE.md) | **Before going public** — secrets, stats, git hygiene |
| [guides/DOCS_CHEATSHEET.md](guides/DOCS_CHEATSHEET.md) | **Cheatsheet** — doc map, commands, FAQ by role |
| [guides/DEVELOPER_ONBOARDING.md](guides/DEVELOPER_ONBOARDING.md) | **Developers:** install & setup |
| [guides/Usage.md](guides/Usage.md) | Per-mode offline setup (A / C / D) |
| [guides/CSYNTH_QUICK_REFERENCE.md](guides/CSYNTH_QUICK_REFERENCE.md) | **`csynth` CLI** — install, proxy on/off, restart, logs |
| [guides/COST_SAVINGS.md](guides/COST_SAVINGS.md) | **Why cost drops** when payload size looks flat |
| [guides/DASHBOARD.md](guides/DASHBOARD.md) | **Live dashboard** — billing & compaction bifurcation |
| [guides/FETCH_BUNDLE.md](guides/FETCH_BUNDLE.md) | WSL ← build server rsync (dev sync) |
| [guides/DEPLOY.md](guides/DEPLOY.md) | **Team lead** — build tarball, optional shared-drive publish |
| [guides/TEAM_ANNOUNCEMENT.md](guides/TEAM_ANNOUNCEMENT.md) | Copy-paste rollout message for Slack/email |
| [guides/CLI_STATS_GUIDE.md](guides/CLI_STATS_GUIDE.md) | Mode A import details                |

## Reports (analysis & proof)

> Corpus reports use **anonymized developer handles** from private offline studies.
> They contain aggregated metrics only — no raw session exports. See [PUBLIC_RELEASE.md](guides/PUBLIC_RELEASE.md).

| Doc                                                                                                | Purpose                    |
| -------------------------------------------------------------------------------------------------- | -------------------------- |
| [reports/SYNTHESIZER_RND_REPORT.md](reports/SYNTHESIZER_RND_REPORT.md) | Full R&D record, roadmap   |
| [reports/DEVELOPER_A_CORPUS_REPORT.md](reports/DEVELOPER_A_CORPUS_REPORT.md)                       | developer-a corpus (32 sessions) |
| [reports/COMPACTION_PROOF_REPORT.md](reports/COMPACTION_PROOF_REPORT.md)                           | developer-a turn-178 deep dive |
| [reports/DEVELOPER_B_CORPUS_REPORT.md](reports/DEVELOPER_B_CORPUS_REPORT.md)                           | developer-b corpus test      |
| [reports/DEVELOPER_C_CORPUS_REPORT.md](reports/DEVELOPER_C_CORPUS_REPORT.md) | developer-c UI session (120 turns) |
| [reports/CORPUS_COMPARATIVE_ANALYSIS.md](reports/CORPUS_COMPARATIVE_ANALYSIS.md)                 | developer-a vs developer-b vs developer-c |
| [reports/BENCHMARK_ANALYSIS.md](reports/BENCHMARK_ANALYSIS.md)                                     | Internal proxy benchmark   |

## Architecture

| Doc                                                              | Purpose                    |
| ---------------------------------------------------------------- | -------------------------- |
| [context_os_technical_report.md](context_os_technical_report.md) | Gateway design, OS analogy — §8.3 has latest corpus numbers |
