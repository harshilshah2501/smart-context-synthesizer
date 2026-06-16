#!/usr/bin/env bash
# Print dashboard URL (WSL-aware) and optionally open in Windows browser.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh" 2>/dev/null || true

REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${REPO_ROOT}/context-synthesizer/.env"
PORT="8080"
PROXY_HOST="127.0.0.1"
DASH_TOKEN=""
if [[ -f "$ENV_FILE" ]]; then
  line="$(grep -E '^PROXY_PORT=' "$ENV_FILE" 2>/dev/null || true)"
  PORT="${line#PROXY_PORT=}"
  line="$(grep -E '^PROXY_HOST=' "$ENV_FILE" 2>/dev/null || true)"
  PROXY_HOST="${line#PROXY_HOST=}"
  line="$(grep -E '^DASHBOARD_TOKEN=' "$ENV_FILE" 2>/dev/null || true)"
  DASH_TOKEN="${line#DASHBOARD_TOKEN=}"
fi
PORT="${PORT:-8080}"
PROXY_HOST="${PROXY_HOST:-127.0.0.1}"

dashboard_url() {
  local base="$1"
  if [[ -n "$DASH_TOKEN" ]]; then
    printf '%s/dashboard?token=%s' "$base" "$DASH_TOKEN"
  else
    printf '%s/dashboard' "$base"
  fi
}

IS_WSL=0
WSL_IP=""
if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
  IS_WSL=1
  WSL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

health() {
  curl -sf --max-time 2 "$1/health" >/dev/null 2>&1
}

echo "Proxy dashboard URLs:"
echo "  WSL / Claude Code:  $(dashboard_url "http://127.0.0.1:${PORT}")"

if [[ -n "$DASH_TOKEN" ]]; then
  echo "  (token required — URLs above include ?token=...)"
fi

if [[ "$IS_WSL" -eq 1 && -n "$WSL_IP" ]]; then
  echo "  Windows browser:    $(dashboard_url "http://${WSL_IP}:${PORT}")"
  echo ""
  echo "  Do NOT use http://127.0.0.1:${PORT}/dashboard in Windows Chrome — that is Windows localhost (ERR_EMPTY_RESPONSE)."
  if ! health "http://${WSL_IP}:${PORT}"; then
    echo ""
    echo "  ⚠ Windows cannot reach the proxy on WSL IP yet."
    if [[ "$PROXY_HOST" == "127.0.0.1" ]]; then
      echo "  Fix: add to ${ENV_FILE}:"
      echo "       PROXY_HOST=0.0.0.0"
      echo "  Then: systemctl --user restart context-synthesizer-proxy"
    else
      echo "  Check: systemctl --user status context-synthesizer-proxy"
    fi
  elif health "http://127.0.0.1:${PORT}"; then
    echo "  ✓ Proxy reachable on WSL IP"
  fi
elif health "http://127.0.0.1:${PORT}"; then
  echo "  ✓ Proxy health OK"
else
  echo ""
  echo "  ⚠ Proxy not responding — run: systemctl --user status context-synthesizer-proxy"
fi

if [[ "${1:-}" == "--open" ]]; then
  if [[ "$IS_WSL" -eq 1 && -n "$WSL_IP" ]]; then
    cmd.exe /c start "$(dashboard_url "http://${WSL_IP}:${PORT}")" 2>/dev/null || true
  else
    cmd.exe /c start "$(dashboard_url "http://127.0.0.1:${PORT}")" 2>/dev/null || \
      xdg-open "$(dashboard_url "http://127.0.0.1:${PORT}")" 2>/dev/null || true
  fi
fi
