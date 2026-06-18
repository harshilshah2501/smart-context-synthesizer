#!/usr/bin/env bash
# Point Claude Code at local context synthesizer proxy (merge settings.json).
#
# WSL: writes TWO configs when Windows Claude Code is detected:
#   • ~/.claude/settings.json           → http://127.0.0.1:PORT  (claude CLI inside WSL)
#   • /mnt/c/Users/<win>/.claude/...    → http://<WSL_IP>:PORT (Claude Code Windows app)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

ENV_FILE="${REPO_ROOT}/context-synthesizer/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

PROXY_PORT="${PROXY_PORT:-8080}"
PY="${REPO_ROOT}/.venv/bin/python"

write_claude_settings() {
  local settings_path="$1"
  local proxy_url="$2"
  local developer_id="$3"
  "$PY" - "$settings_path" "$proxy_url" "$developer_id" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
proxy_url = sys.argv[2]
developer_id = sys.argv[3]

data: dict = {}
if settings_path.is_file():
    data = json.loads(settings_path.read_text(encoding="utf-8"))

env = data.setdefault("env", {})
env["ANTHROPIC_BASE_URL"] = proxy_url
env["TELEMETRY_DEVELOPER_ID"] = developer_id

settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Updated {settings_path}")
print(f"  ANTHROPIC_BASE_URL={proxy_url}")
print(f"  TELEMETRY_DEVELOPER_ID={developer_id}")
PY
}

IS_WSL=0
WSL_IP=""
if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
  IS_WSL=1
  WSL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

# WSL / native Linux: Claude Code in the same environment as the proxy
WSL_PROXY_URL="${SYNTH_PROXY_URL:-http://127.0.0.1:${PROXY_PORT}}"
WSL_SETTINGS="${CLAUDE_SETTINGS_PATH:-$HOME/.claude/settings.json}"

echo "Configuring Claude Code (WSL / terminal) → $WSL_PROXY_URL"
write_claude_settings "$WSL_SETTINGS" "$WSL_PROXY_URL" "$TELEMETRY_DEVELOPER_ID"

if [[ "$IS_WSL" -eq 1 && -n "$WSL_IP" ]]; then
  WIN_USER=""
  if command -v cmd.exe >/dev/null 2>&1; then
    WIN_USER="$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n' || true)"
  fi
  if [[ -n "$WIN_USER" && -d "/mnt/c/Users/${WIN_USER}" ]]; then
    WIN_SETTINGS="/mnt/c/Users/${WIN_USER}/.claude/settings.json"
    WIN_PROXY_URL="http://${WSL_IP}:${PROXY_PORT}"
    echo ""
    echo "Configuring Claude Code (Windows app) → $WIN_PROXY_URL"
    echo "  (Windows cannot use 127.0.0.1 to reach the WSL proxy)"
    write_claude_settings "$WIN_SETTINGS" "$WIN_PROXY_URL" "$TELEMETRY_DEVELOPER_ID"
    echo ""
    echo "Restart Claude Code on Windows after this change."
  else
    echo ""
    echo "Note: Windows Claude settings not updated (could not find /mnt/c/Users/<user>)."
    echo "  If you use Claude Code on Windows (not inside WSL), set manually:"
    echo "    ANTHROPIC_BASE_URL=http://${WSL_IP}:${PROXY_PORT}"
    echo "  in %USERPROFILE%\\.claude\\settings.json"
  fi
fi
