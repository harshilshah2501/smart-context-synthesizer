#!/usr/bin/env bash
# Point Claude Code at local context synthesizer proxy (merge settings.json).
#
# Configures THREE places (when applicable):
#   • ~/.claude/settings.json              — Claude CLI / terminal
#   • Windows %USERPROFILE%\.claude\...    — Claude desktop (WSL IP)
#   • VS Code User settings.json           — claudeCode.environmentVariables
#     (Claude Code VS Code extension does NOT read ~/.claude/settings.json)
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

write_vscode_claude_settings() {
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
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"WARN: could not parse {settings_path}: {exc}", file=sys.stderr)
        data = {}

# Claude Code VS Code extension reads claudeCode.environmentVariables — NOT ~/.claude/settings.json
desired = {
    "ANTHROPIC_BASE_URL": proxy_url,
    "TELEMETRY_DEVELOPER_ID": developer_id,
}
existing = data.get("claudeCode.environmentVariables")
if not isinstance(existing, list):
    existing = []
merged: list[dict] = []
seen: set[str] = set()
for item in existing:
    if isinstance(item, dict):
        name = item.get("name") or item.get("key")  # "key" was an old typo in docs
        if name and name not in desired:
            merged.append({"name": name, "value": item.get("value", "")})
            seen.add(name)
for name, value in desired.items():
    merged.append({"name": name, "value": value})
    seen.add(name)

data["claudeCode.environmentVariables"] = merged
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Updated VS Code {settings_path}")
for name, value in desired.items():
    print(f"  claudeCode.environmentVariables → {name}={value}")
PY
}

IS_WSL=0
WSL_IP=""
if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
  IS_WSL=1
  WSL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

WIN_USER=""
if command -v cmd.exe >/dev/null 2>&1; then
  WIN_USER="$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n' || true)"
fi

# WSL / native Linux: Claude Code in the same environment as the proxy
WSL_PROXY_URL="${SYNTH_PROXY_URL:-http://127.0.0.1:${PROXY_PORT}}"
WSL_SETTINGS="${CLAUDE_SETTINGS_PATH:-$HOME/.claude/settings.json}"

echo "=== 1/3 Claude CLI / terminal (~/.claude/settings.json) ==="
echo "Configuring → $WSL_PROXY_URL"
write_claude_settings "$WSL_SETTINGS" "$WSL_PROXY_URL" "$TELEMETRY_DEVELOPER_ID"

WIN_PROXY_URL=""
if [[ "$IS_WSL" -eq 1 && -n "$WSL_IP" ]]; then
  WIN_PROXY_URL="http://${WSL_IP}:${PROXY_PORT}"
elif [[ "$IS_WSL" -eq 0 ]]; then
  WIN_PROXY_URL="$WSL_PROXY_URL"
fi

if [[ -n "$WIN_PROXY_URL" && -n "$WIN_USER" && -d "/mnt/c/Users/${WIN_USER}" ]]; then
  echo ""
  echo "=== 2/3 Claude desktop / Windows (~/.claude/settings.json) ==="
  echo "Configuring → $WIN_PROXY_URL"
  write_claude_settings "/mnt/c/Users/${WIN_USER}/.claude/settings.json" "$WIN_PROXY_URL" "$TELEMETRY_DEVELOPER_ID"
fi

echo ""
echo "=== 3/3 Claude Code VS Code extension (User settings.json) ==="
VSCODE_CONFIGURED=0
VSCODE_URL="${WIN_PROXY_URL:-$WSL_PROXY_URL}"

if [[ -n "$WIN_USER" && -d "/mnt/c/Users/${WIN_USER}/AppData/Roaming/Code/User" ]]; then
  VSCODE_WIN="/mnt/c/Users/${WIN_USER}/AppData/Roaming/Code/User/settings.json"
  echo "Configuring Windows VS Code → $VSCODE_URL"
  write_vscode_claude_settings "$VSCODE_WIN" "$VSCODE_URL" "$TELEMETRY_DEVELOPER_ID"
  VSCODE_CONFIGURED=1
fi

if [[ -d "$HOME/.config/Code/User" ]]; then
  VSCODE_LINUX="$HOME/.config/Code/User/settings.json"
  echo "Configuring Linux/WSL VS Code → $WSL_PROXY_URL"
  write_vscode_claude_settings "$VSCODE_LINUX" "$WSL_PROXY_URL" "$TELEMETRY_DEVELOPER_ID"
  VSCODE_CONFIGURED=1
fi

if [[ "$VSCODE_CONFIGURED" -eq 0 ]]; then
  echo "VS Code settings.json not found — add manually in VS Code:"
  echo '  Settings → Claude Code: Environment Variables → Edit in settings.json'
  echo '  "claudeCode.environmentVariables": ['
  echo '    {"name": "ANTHROPIC_BASE_URL", "value": "http://<WSL_IP>:8080"},'
  echo '    {"name": "TELEMETRY_DEVELOPER_ID", "value": "'"$TELEMETRY_DEVELOPER_ID"'"}'
  echo '  ]'
fi

echo ""
echo "Restart VS Code / Claude Code after this change."
echo "Verbose proxy trace: journalctl --user -u context-synthesizer-proxy -f | grep -E '\\[ACCESS\\]|\\[PROXY\\]'"
