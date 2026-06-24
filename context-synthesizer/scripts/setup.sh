#!/usr/bin/env bash
# One-time setup: venv for the context-synthesizer proxy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
VENV="$REPO_ROOT/.venv"

cd "$REPO_ROOT"

if [[ ! -d "$VENV" ]]; then
  echo "Creating venv at $VENV"
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$REPO_ROOT/context-synthesizer/requirements.txt"

if ! "$VENV/bin/python" -c "import anyio._backends._asyncio" 2>/dev/null; then
  echo "WARN: anyio backend missing after install — run repair_venv.sh" >&2
fi

mkdir -p "$REPO_ROOT/context-synthesizer/stats"

echo ""
echo "Setup complete."
echo "  Python:  $VENV/bin/python"
echo "  Onboard: context-synthesizer/scripts/setup_developer.sh --developer YOU"
