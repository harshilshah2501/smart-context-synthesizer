#!/usr/bin/env bash
# Team lead: pull developer uploads from shared drive into stats/inbox/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SYNTH_DIR/.." && pwd)"
INBOX="$SYNTH_DIR/stats/inbox"

RCLONE_REMOTE="${1:-${RCLONE_REMOTE:-}}"
if [[ -z "$RCLONE_REMOTE" ]]; then
  echo "Usage: $0 <rclone-remote:path>" >&2
  echo "  Example: $0 'gdrive:Shared/ContextSynthesizer/weekly'" >&2
  exit 1
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone not installed." >&2
  exit 1
fi

mkdir -p "$INBOX"
echo "Syncing ${RCLONE_REMOTE}/ → $INBOX"
rclone sync "$RCLONE_REMOTE" "$INBOX" --include '*.jsonl' --include '*.csv' --include '*.json' --include '*.md'

echo "Run team rollup:"
echo "  bash context-synthesizer/scripts/team_rollup.sh"
