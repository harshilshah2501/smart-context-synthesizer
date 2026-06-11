#!/usr/bin/env bash
# Import Claude Code backup zip (Mode D) — for devs who share ~/.claude exports.
#
# Usage:
#   context-synthesizer/scripts/import_claude_backup.sh path/to/backup.zip
#   context-synthesizer/scripts/import_claude_backup.sh backup.zip --developer meet-chavda
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SYNTH_DIR/.." && pwd)"

PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

ZIP=""
DEVELOPER="${TELEMETRY_DEVELOPER_ID:-$(whoami)}"
MIN_TURNS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --developer) DEVELOPER="$2"; shift 2 ;;
    --min-turns) MIN_TURNS="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      if [[ -z "$ZIP" ]]; then
        ZIP="$1"
      else
        echo "Unexpected argument: $1" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$ZIP" || ! -f "$ZIP" ]]; then
  echo "Usage: $0 <backup.zip> [--developer HANDLE]" >&2
  exit 1
fi

SAFE_DEV="$(echo "$DEVELOPER" | tr '/ ' '__')"
EXTRACT_ROOT="$SYNTH_DIR/stats/backups/${SAFE_DEV}"
CLI_ROOT="$EXTRACT_ROOT/.claude/projects"
WEEK="$(date +%Y-%m-%d)"
OUT_JSONL="$SYNTH_DIR/stats/weekly/${WEEK}_${DEVELOPER}_claude_backup.jsonl"
OUT_CSV="$SYNTH_DIR/stats/weekly/${WEEK}_${DEVELOPER}_claude_backup.csv"

mkdir -p "$EXTRACT_ROOT" "$(dirname "$OUT_JSONL")"

echo "Extracting $ZIP → $EXTRACT_ROOT"
unzip -qo "$ZIP" -d "$EXTRACT_ROOT"

if [[ ! -d "$CLI_ROOT" ]]; then
  # Some zips nest .claude at top level; others export projects/ only
  FOUND="$(find "$EXTRACT_ROOT" -type d -path '*/.claude/projects' 2>/dev/null | head -1)"
  if [[ -n "$FOUND" ]]; then
    CLI_ROOT="$FOUND"
  elif [[ -d "$EXTRACT_ROOT/projects" ]]; then
    CLI_ROOT="$EXTRACT_ROOT/projects"
  else
    FOUND="$(find "$EXTRACT_ROOT" -type d -name projects 2>/dev/null | head -1)"
    if [[ -n "$FOUND" ]]; then
      CLI_ROOT="$FOUND"
    else
      echo "ERROR: no projects/ or .claude/projects found inside zip" >&2
      exit 1
    fi
  fi
fi
echo "Using CLI root: $CLI_ROOT"

"$PY" "$SYNTH_DIR/import_claude_sessions.py" \
  --cli-root "$CLI_ROOT" \
  --developer "$DEVELOPER" \
  --min-turns "$MIN_TURNS" \
  --output "$OUT_JSONL" \
  --export "$OUT_CSV"

echo ""
echo "Imported backup → $OUT_JSONL"
