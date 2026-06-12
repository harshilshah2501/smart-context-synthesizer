#!/usr/bin/env bash
# One-time setup for context-synthesizer corpus workflow (Modes A/C/D).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV="$REPO_ROOT/.venv"

cd "$REPO_ROOT"

if [[ ! -d "$VENV" ]]; then
  echo "Creating venv at $VENV"
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$REPO_ROOT/context-synthesizer/requirements.txt"

mkdir -p "$REPO_ROOT/context-synthesizer/stats/weekly"
mkdir -p "$REPO_ROOT/context-synthesizer/stats/inbox"

echo ""
echo "Setup complete."
echo "  Python:  $VENV/bin/python"
echo "  Export:  context-synthesizer/scripts/export_weekly_corpus.sh --mode d"
echo "  Onboard: context-synthesizer/scripts/setup_developer.sh --developer YOU"
echo "  Deploy:  docs/guides/DEPLOY.md"
