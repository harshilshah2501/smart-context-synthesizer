#!/usr/bin/env bash
# Install Monday morning cron for weekly_sync.sh (idempotent marker).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

CRON_HOUR="${CRON_HOUR:-9}"
CRON_DOW="${CRON_DOW:-1}"
MARKER="# context-synthesizer-weekly"
LINE="0 ${CRON_HOUR} * * ${CRON_DOW} ${SCRIPT_DIR}/weekly_sync.sh ${MARKER}"

TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$MARKER" >"$TMP" || true
echo "$LINE" >>"$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "Cron installed: Mondays ${CRON_HOUR}:00 → weekly_sync.sh"
echo "Logs: ${XDG_STATE_HOME:-$HOME/.local/state}/context-synthesizer/"
