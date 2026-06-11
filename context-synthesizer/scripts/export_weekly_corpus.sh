#!/usr/bin/env bash
# Weekly corpus export for one developer (Mode D, C, or A).
#
# Usage:
#   export TELEMETRY_DEVELOPER_ID=your-github-handle
#   context-synthesizer/scripts/export_weekly_corpus.sh --mode d
#   context-synthesizer/scripts/export_weekly_corpus.sh --mode cursor --project m-coder
#   context-synthesizer/scripts/export_weekly_corpus.sh --mode a
#   context-synthesizer/scripts/export_weekly_corpus.sh --mode all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SYNTH_DIR/.." && pwd)"

PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

MODE="d"
DEVELOPER="${TELEMETRY_DEVELOPER_ID:-$(whoami)}"
CURSOR_PROJECT=""
MIN_TURNS=25
WEEK="$(date +%Y-%m-%d)"
OUT_DIR="$SYNTH_DIR/stats/weekly"
SINCE=""

usage() {
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --developer) DEVELOPER="$2"; shift 2 ;;
    --project) CURSOR_PROJECT="$2"; shift 2 ;;
    --min-turns) MIN_TURNS="$2"; shift 2 ;;
    --week) WEEK="$2"; shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

mkdir -p "$OUT_DIR"

export_claude() {
  local jsonl="$OUT_DIR/${WEEK}_${DEVELOPER}_claude.jsonl"
  local csv="$OUT_DIR/${WEEK}_${DEVELOPER}_claude.csv"
  local hot="$OUT_DIR/${WEEK}_${DEVELOPER}_hot_claude.json"

  "$PY" "$SYNTH_DIR/import_claude_sessions.py" \
    --developer "$DEVELOPER" \
    --min-turns "$MIN_TURNS" \
    --output "$jsonl" \
    --export "$csv"

  "$PY" "$SYNTH_DIR/analyze_hot_session.py" \
    --source claude \
    --largest \
    --export "$hot"

  echo ""
  echo "Claude (Mode D) → $jsonl"
  echo "  CSV: $csv"
  echo "  Hot: $hot"
}

export_cursor() {
  local jsonl="$OUT_DIR/${WEEK}_${DEVELOPER}_cursor.jsonl"
  local hot="$OUT_DIR/${WEEK}_${DEVELOPER}_hot_cursor.json"
  local args=(--developer "$DEVELOPER" --min-turns "$MIN_TURNS" --output "$jsonl")

  if [[ -n "$CURSOR_PROJECT" ]]; then
    args+=(--project "$CURSOR_PROJECT")
  fi

  "$PY" "$SYNTH_DIR/import_cursor_sessions.py" "${args[@]}"

  local hot_args=(--source cursor --largest --export "$hot")
  if [[ -n "$CURSOR_PROJECT" ]]; then
    hot_args+=(--project "$CURSOR_PROJECT")
  fi
  "$PY" "$SYNTH_DIR/analyze_hot_session.py" "${hot_args[@]}"

  echo ""
  echo "Cursor (Mode C) → $jsonl"
  echo "  Hot: $hot"
}

export_cli() {
  local jsonl="$OUT_DIR/${WEEK}_${DEVELOPER}_cli.jsonl"
  local args=(--output "$jsonl" --developer "$DEVELOPER")

  if [[ -n "$SINCE" ]]; then
    args+=(--since "$SINCE")
  fi

  "$PY" "$SYNTH_DIR/import_cli_logs.py" "${args[@]}"

  echo ""
  echo "Claude CLI (Mode A) → $jsonl"
}

case "$MODE" in
  d|claude) export_claude ;;
  c|cursor) export_cursor ;;
  a|cli) export_cli ;;
  all)
    export_claude
    export_cursor
  ;;
  *)
    echo "Invalid --mode: $MODE (use d, cursor, a, or all)" >&2
    exit 1
  ;;
esac

echo ""
echo "Upload these files to the team inbox (see DEPLOY.md):"
echo "  $OUT_DIR/${WEEK}_${DEVELOPER}_*"
