#!/usr/bin/env bash
# Fix broken venv deps (e.g. ModuleNotFoundError: No module named 'anyio._backends').
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
VENV="$REPO_ROOT/.venv"
REQ="$REPO_ROOT/context-synthesizer/requirements.txt"

if [[ ! -x "$VENV/bin/pip" ]]; then
  echo "No venv at $VENV — run: bash context-synthesizer/scripts/setup.sh" >&2
  exit 1
fi

echo "Repairing Python dependencies in $VENV ..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install --force-reinstall -r "$REQ"

echo "Verifying imports ..."
"$VENV/bin/python" -c "
import anyio._backends._asyncio  # noqa: F401 — ensure backend submodule present
import fastapi, uvicorn, anthropic, httpx
print('OK: fastapi', fastapi.__version__, 'anyio backend loaded')
"

echo ""
echo "Restart proxy:"
echo "  systemctl --user restart context-synthesizer-proxy"
echo "  systemctl --user status context-synthesizer-proxy"
