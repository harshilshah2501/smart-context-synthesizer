#!/usr/bin/env bash
# Point Claude Code at local context synthesizer proxy (merge settings.json).
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

# Claude Code runs locally; PROXY_HOST=0.0.0.0 is for dashboard bind only.
if [[ -z "${SYNTH_PROXY_URL:-}" ]]; then
  PROXY_PORT="${PROXY_PORT:-8080}"
  export SYNTH_PROXY_URL="http://127.0.0.1:${PROXY_PORT}"
fi

PY="${REPO_ROOT}/.venv/bin/python"
SETTINGS="${CLAUDE_SETTINGS_PATH:-$HOME/.claude/settings.json}"

"$PY" - "$SETTINGS" "$TELEMETRY_DEVELOPER_ID" <<'PY'
import json
import os
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
developer_id = sys.argv[2]
proxy_url = os.environ.get("SYNTH_PROXY_URL", "http://127.0.0.1:8080")

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
