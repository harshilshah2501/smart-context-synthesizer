#!/usr/bin/env bash
# systemd ExecStart launcher — correct cwd, load .env, forward exit codes to journal.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"

if [[ -z "${REPO_ROOT:-}" ]]; then
  load_developer_config
fi

PY="${REPO_ROOT}/.venv/bin/python"
PROXY_PY="${REPO_ROOT}/context-synthesizer/proxy_tool.py"
ENV_FILE="${REPO_ROOT}/context-synthesizer/.env"

if [[ ! -x "$PY" ]]; then
  echo "context-synthesizer-proxy: missing venv python at $PY — re-run setup_developer.sh" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

cd "${REPO_ROOT}/context-synthesizer"
exec "$PY" "$PROXY_PY"
