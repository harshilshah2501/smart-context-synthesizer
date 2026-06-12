#!/usr/bin/env bash
# Upload weekly export: copy to OneDrive sync folder (no rclone) OR rclone remote.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

WEEK="${1:-$(date +%Y-%m-%d)}"
SYNTH_DIR="$REPO_ROOT/context-synthesizer"
OUT_DIR="$SYNTH_DIR/stats/weekly"

shopt -s nullglob
FILES=(
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_claude.jsonl"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_claude.csv"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_hot_claude.json"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_summary.md"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_cursor.jsonl"
  "$OUT_DIR/${WEEK}_${TELEMETRY_DEVELOPER_ID}_hot_cursor.json"
)

upload_via_sync_dir() {
  local dest="${SYNC_DIR%/}"
  mkdir -p "$dest"
  local uploaded=0
  for f in "${FILES[@]}"; do
    [[ -f "$f" ]] || continue
    echo "Copying $(basename "$f") → $dest/"
    cp -f "$f" "$dest/"
    uploaded=$((uploaded + 1))
  done
  if [[ "$uploaded" -eq 0 ]]; then
    echo "No files to upload for week $WEEK — run export first." >&2
    exit 1
  fi
  echo "Copied $uploaded file(s) to $dest/ (OneDrive will sync to SharePoint)"
}

upload_via_rclone() {
  if ! command -v rclone >/dev/null 2>&1; then
    echo "rclone not installed. Use --sync-dir with OneDrive instead." >&2
    exit 1
  fi
  local uploaded=0
  for f in "${FILES[@]}"; do
    [[ -f "$f" ]] || continue
    echo "Uploading $(basename "$f") → ${RCLONE_REMOTE}/"
    rclone copyto "$f" "${RCLONE_REMOTE}/$(basename "$f")"
    uploaded=$((uploaded + 1))
  done
  if [[ "$uploaded" -eq 0 ]]; then
    echo "No files to upload for week $WEEK — run export first." >&2
    exit 1
  fi
  echo "Uploaded $uploaded file(s) to ${RCLONE_REMOTE}/"
}

if [[ -n "${SYNC_DIR:-}" ]]; then
  upload_via_sync_dir
elif [[ -n "${RCLONE_REMOTE:-}" ]]; then
  upload_via_rclone
else
  echo "No upload target — set SYNC_DIR or RCLONE_REMOTE in $CONFIG_FILE" >&2
  exit 0
fi
