#!/usr/bin/env bash
# Remove ANTHROPIC_BASE_URL from Claude Code settings (direct Anthropic API).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

PY="${REPO_ROOT}/.venv/bin/python"

clear_claude_settings() {
  local settings_path="$1"
  "$PY" - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
if not settings_path.is_file():
    print(f"Skip (missing): {settings_path}")
    raise SystemExit(0)

data = json.loads(settings_path.read_text(encoding="utf-8"))
env = data.get("env")
if isinstance(env, dict) and "ANTHROPIC_BASE_URL" in env:
    del env["ANTHROPIC_BASE_URL"]
    if not env:
        data.pop("env", None)
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Cleared ANTHROPIC_BASE_URL in {settings_path}")
else:
    print(f"No ANTHROPIC_BASE_URL in {settings_path}")
PY
}

clear_vscode_claude_settings() {
  local settings_path="$1"
  "$PY" - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
if not settings_path.is_file():
    print(f"Skip (missing): {settings_path}")
    raise SystemExit(0)

try:
    data = json.loads(settings_path.read_text(encoding="utf-8"))
except json.JSONDecodeError as exc:
    print(f"WARN: could not parse {settings_path}: {exc}", file=sys.stderr)
    raise SystemExit(0)

existing = data.get("claudeCode.environmentVariables")
if not isinstance(existing, list):
    print(f"No claudeCode.environmentVariables in {settings_path}")
    raise SystemExit(0)

filtered = [
    item for item in existing
    if not (isinstance(item, dict) and (item.get("name") or item.get("key")) == "ANTHROPIC_BASE_URL")
]
if len(filtered) == len(existing):
    print(f"No ANTHROPIC_BASE_URL in VS Code {settings_path}")
    raise SystemExit(0)

if filtered:
    data["claudeCode.environmentVariables"] = filtered
else:
    data.pop("claudeCode.environmentVariables", None)

settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(f"Cleared ANTHROPIC_BASE_URL in VS Code {settings_path}")
PY
}

WIN_USER=""
if command -v cmd.exe >/dev/null 2>&1; then
  WIN_USER="$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n' || true)"
fi

WSL_SETTINGS="${CLAUDE_SETTINGS_PATH:-$HOME/.claude/settings.json}"

echo "=== 1/3 Claude CLI / terminal (~/.claude/settings.json) ==="
clear_claude_settings "$WSL_SETTINGS"

if [[ -n "$WIN_USER" && -d "/mnt/c/Users/${WIN_USER}" ]]; then
  echo ""
  echo "=== 2/3 Claude desktop / Windows (~/.claude/settings.json) ==="
  clear_claude_settings "/mnt/c/Users/${WIN_USER}/.claude/settings.json"
fi

echo ""
echo "=== 3/3 Claude Code VS Code extension (User settings.json) ==="
if [[ -n "$WIN_USER" && -d "/mnt/c/Users/${WIN_USER}/AppData/Roaming/Code/User" ]]; then
  clear_vscode_claude_settings "/mnt/c/Users/${WIN_USER}/AppData/Roaming/Code/User/settings.json"
fi
if [[ -d "$HOME/.config/Code/User" ]]; then
  clear_vscode_claude_settings "$HOME/.config/Code/User/settings.json"
fi

echo ""
echo "Claude Code will use Anthropic directly. Restart VS Code / Claude Code."
