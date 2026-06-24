#!/usr/bin/env bash
# Enable or disable live compaction proxy (routing + optional systemd service).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/context-synthesizer"
CONFIG_FILE="$CONFIG_DIR/developer.env"

usage() {
  echo "Usage: set_proxy_enabled.sh on|off" >&2
  exit 1
}

[[ $# -eq 1 ]] || usage
MODE="$1"
case "$MODE" in
  on|off) ;;
  *) usage ;;
esac

# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

_set_enable_proxy_flag() {
  local val="$1"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Missing $CONFIG_FILE — run setup first." >&2
    exit 1
  fi
  if grep -q '^ENABLE_PROXY=' "$CONFIG_FILE"; then
    sed -i "s/^ENABLE_PROXY=.*/ENABLE_PROXY=${val}/" "$CONFIG_FILE"
  else
    echo "ENABLE_PROXY=${val}" >>"$CONFIG_FILE"
  fi
}

if [[ "$MODE" == on ]]; then
  echo "=== Enabling Context Synthesizer proxy ==="
  bash "$SCRIPT_DIR/configure_claude_proxy.sh"
  UNIT="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/context-synthesizer-proxy.service"
  if [[ -f "$UNIT" ]]; then
    systemctl --user enable --now context-synthesizer-proxy.service
  else
    bash "$SCRIPT_DIR/install_proxy_service.sh"
  fi
  _set_enable_proxy_flag 1
  echo ""
  echo "Proxy ON — Claude Code routes through the synthesizer."
  echo "  csynth status | csynth dashboard"
else
  echo "=== Disabling Context Synthesizer proxy ==="
  bash "$SCRIPT_DIR/disable_claude_proxy.sh"
  if systemctl --user is-active --quiet context-synthesizer-proxy.service 2>/dev/null; then
    systemctl --user stop context-synthesizer-proxy.service
    echo "Stopped context-synthesizer-proxy service."
  fi
  _set_enable_proxy_flag 0
  echo ""
  echo "Proxy OFF — Claude Code uses Anthropic directly."
fi
