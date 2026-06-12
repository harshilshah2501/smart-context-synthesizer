#!/usr/bin/env bash
# Load ~/.config/context-synthesizer/developer.env (created by setup_developer.sh).
set -euo pipefail

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/context-synthesizer"
CONFIG_FILE="$CONFIG_DIR/developer.env"

load_developer_config() {
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Missing $CONFIG_FILE — run: bash context-synthesizer/scripts/setup_developer.sh --developer YOUR_HANDLE" >&2
    return 1
  fi
  # shellcheck disable=SC1090
  set -a
  source "$CONFIG_FILE"
  set +a

  if [[ -z "${REPO_ROOT:-}" || ! -d "$REPO_ROOT" ]]; then
    echo "REPO_ROOT invalid in $CONFIG_FILE" >&2
    return 1
  fi
  if [[ -z "${TELEMETRY_DEVELOPER_ID:-}" ]]; then
    echo "TELEMETRY_DEVELOPER_ID not set in $CONFIG_FILE" >&2
    return 1
  fi
  EXPORT_MODE="${EXPORT_MODE:-d}"
  RCLONE_REMOTE="${RCLONE_REMOTE:-}"
  ENABLE_PROXY="${ENABLE_PROXY:-0}"
}
