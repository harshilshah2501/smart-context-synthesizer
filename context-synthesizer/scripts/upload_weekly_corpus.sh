#!/usr/bin/env bash
# Upload this week's export + summary to shared drive via rclone.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

WEEK="${1:-$(date +%Y-%m-%d)}"
SYNTH_DIR="$REPO_ROOT/context-synthesizer"
OUT_DIR="$SYNTH_DIR/stats/weekly"

if [[ -z "${RCLONE_REMOTE:-}" ]]; then
  echo "RCLONE_REMOTE not set — skip upload (add to $CONFIG_FILE or re-run setup_developer.sh)" >&2
  exit 0
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone not installed. Install: https://rclone.org/install/" >&2
  exit 1
fi

shopt -s nullglob
FILES=(
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_claude.jsonl"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_claude.csv"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_hot_claude.json"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_summary.md"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_cursor.jsonl"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_hot_cursor.json"
)

UPLOADED=0
for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || continue
  echo "Uploading $(basename "$f") → ${RCLONE_REMOTE}/"
  rclone copyto "$f" "${RCLONE_REMOTE}/$(basename "$f")"
  UPLOADED=$((UPLOADED + 1))
done

if [[ "$UPLOADED" -eq 0 ]]; then
  echo "No files to upload for week $WEEK — run export first." >&2
  exit 1
fi

echo "Uploaded $UPLOADED file(s) to ${RCLONE_REMOTE}/"
