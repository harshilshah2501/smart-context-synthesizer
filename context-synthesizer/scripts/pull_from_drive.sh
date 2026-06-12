#!/usr/bin/env bash
# Team lead: pull developer uploads into stats/inbox/ (OneDrive folder or rclone).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INBOX="$SYNTH_DIR/stats/inbox"

SOURCE="${1:-}"
SYNC_DIR="${SYNC_DIR:-}"

usage() {
  echo "Usage: $0 <local-onedrive-folder>|rclone-remote:path" >&2
  echo "  Local:  $0 '/home/you/OneDrive - Motadata/ContextSynthesizer/weekly'" >&2
  echo "  rclone: $0 'gdrive:Shared/ContextSynthesizer/weekly'" >&2
  exit 1
}

[[ -n "$SOURCE" ]] || usage
mkdir -p "$INBOX"

if [[ -d "$SOURCE" ]]; then
  echo "Copying $SOURCE → $INBOX"
  shopt -s nullglob
  for f in "$SOURCE"/*.{jsonl,csv,json,md}; do
    [[ -f "$f" ]] || continue
    cp -f "$f" "$INBOX/"
  done
elif [[ "$SOURCE" == *:* ]]; then
  if ! command -v rclone >/dev/null 2>&1; then
    echo "rclone not installed." >&2
    exit 1
  fi
  echo "Syncing $SOURCE → $INBOX"
  rclone sync "$SOURCE" "$INBOX" --include '*.jsonl' --include '*.csv' --include '*.json' --include '*.md'
else
  echo "Not a directory or rclone remote: $SOURCE" >&2
  exit 1
fi

echo "Run team rollup:"
echo "  bash context-synthesizer/scripts/team_rollup.sh"
