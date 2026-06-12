#!/usr/bin/env bash
# Preflight before enabling context-synthesizer-proxy (imports, Claude.md, port).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"

_FALLBACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -f "$CONFIG_FILE" ]]; then
  load_developer_config 2>/dev/null || true
fi
if [[ -z "${REPO_ROOT:-}" || ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  REPO_ROOT="$_FALLBACK_ROOT"
fi
PY="${REPO_ROOT}/.venv/bin/python"
ENV_FILE="${REPO_ROOT}/context-synthesizer/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

PORT="${PROXY_PORT:-8080}"
FAIL=0

say() { echo "check_proxy_ready: $*" >&2; }

if [[ ! -x "$PY" ]]; then
  say "missing venv — run: bash $REPO_ROOT/context-synthesizer/scripts/setup.sh"
  exit 1
fi

if ! "$PY" -c "import fastapi, uvicorn, anthropic" 2>/dev/null; then
  say "missing proxy dependencies — run: bash $REPO_ROOT/context-synthesizer/scripts/setup.sh"
  exit 1
fi

if [[ ! -f "${REPO_ROOT}/context-synthesizer/Claude.md" ]]; then
  say "missing ${REPO_ROOT}/context-synthesizer/Claude.md"
  exit 1
fi

if ! "$PY" -c "
import socket, sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('127.0.0.1', port))
except OSError as e:
    print(f'port {port} in use ({e})', file=sys.stderr)
    sys.exit(1)
finally:
    s.close()
" "$PORT"; then
  say "free port $PORT or set PROXY_PORT=8081 in $ENV_FILE then re-run install_proxy_service.sh"
  exit 1
fi

# Brief startup smoke — curl /health (timeout exit 124 is OK; exit 1 is a real crash)
LOG="$(mktemp)"
set +e
"$PY" "${REPO_ROOT}/context-synthesizer/proxy_tool.py" >"$LOG" 2>&1 &
PROXY_PID=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    kill "$PROXY_PID" 2>/dev/null
    wait "$PROXY_PID" 2>/dev/null || true
    rm -f "$LOG"
    echo "check_proxy_ready: OK (port $PORT, deps, Claude.md)"
    exit 0
  fi
  if ! kill -0 "$PROXY_PID" 2>/dev/null; then
    break
  fi
  sleep 0.5
done
kill "$PROXY_PID" 2>/dev/null
wait "$PROXY_PID" 2>/dev/null || true
set -e
say "proxy failed to start on port $PORT — log:"
tail -n 20 "$LOG" >&2 || true
rm -f "$LOG"
say "run manually: $PY ${REPO_ROOT}/context-synthesizer/proxy_tool.py"
exit 1
