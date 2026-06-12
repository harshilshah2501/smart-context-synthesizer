#!/usr/bin/env bash
# Cron-friendly: export corpus + write summary + upload to shared drive.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

PY="${REPO_ROOT}/.venv/bin/python"
WEEK="$(date +%Y-%m-%d)"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/context-synthesizer"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/weekly-${WEEK}.log"

exec >>"$LOG" 2>&1
echo "=== weekly_sync $(date -Iseconds) ==="

export TELEMETRY_DEVELOPER_ID
bash "$SCRIPT_DIR/export_weekly_corpus.sh" --mode "${EXPORT_MODE:-d}" --developer "$TELEMETRY_DEVELOPER_ID" --week "$WEEK"

CSV="$REPO_ROOT/context-synthesizer/stats/weekly/${WEEK}_${TELEMETRY_DEVELOPER_ID}_claude.csv"
SUMMARY="$REPO_ROOT/context-synthesizer/stats/weekly/${WEEK}_${TELEMETRY_DEVELOPER_ID}_summary.md"

if [[ -f "$CSV" ]]; then
  "$PY" "$SCRIPT_DIR/generate_weekly_summary.py" \
    "$CSV" "$TELEMETRY_DEVELOPER_ID" "$WEEK" "$SUMMARY"
  echo "Summary → $SUMMARY"
fi

bash "$SCRIPT_DIR/upload_weekly_corpus.sh" "$WEEK" || true

echo "Done."
