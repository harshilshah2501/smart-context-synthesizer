#!/usr/bin/env bash
# Print dashboard URL (WSL-aware) and optionally open in Windows browser.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh" 2>/dev/null || true

REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${REPO_ROOT}/context-synthesizer/.env"
PORT="8080"
if [[ -f "$ENV_FILE" ]]; then
  line="$(grep -E '^PROXY_PORT=' "$ENV_FILE" 2>/dev/null || true)"
  PORT="${line#PROXY_PORT=}"
fi
PORT="${PORT:-8080}"

WSL_IP=""
if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
  WSL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

echo "Proxy dashboard URLs:"
echo "  WSL / Linux:  http://127.0.0.1:${PORT}/dashboard"
if [[ -n "$WSL_IP" ]]; then
  echo "  Windows browser (use this if 127.0.0.1 fails): http://${WSL_IP}:${PORT}/dashboard"
fi

if [[ "${1:-}" == "--open" ]] && [[ -n "$WSL_IP" ]]; then
  cmd.exe /c start "http://${WSL_IP}:${PORT}/dashboard" 2>/dev/null || true
fi
