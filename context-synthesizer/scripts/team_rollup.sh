#!/usr/bin/env bash
# Team lead: aggregate developer weekly exports + optional Phase 2 regression.
#
# Usage:
#   # Copy dev uploads into stats/inbox/ first, then:
#   context-synthesizer/scripts/team_rollup.sh
#   context-synthesizer/scripts/team_rollup.sh --validate
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNTH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SYNTH_DIR/.." && pwd)"

PY="${REPO_ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

INBOX="$SYNTH_DIR/stats/inbox"
WEEKLY="$SYNTH_DIR/stats/weekly"
REPORT_DIR="$SYNTH_DIR/stats/reports"
WEEK="$(date +%Y-%m-%d)"
VALIDATE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --validate) VALIDATE=true; shift ;;
    --week) WEEK="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

mkdir -p "$INBOX" "$REPORT_DIR"

# Merge inbox + local weekly exports into one scan set
LOG_DIRS=()
if compgen -G "$INBOX/*.jsonl" > /dev/null; then
  LOG_DIRS+=("$INBOX")
fi
if compgen -G "$WEEKLY/*.jsonl" > /dev/null; then
  LOG_DIRS+=("$WEEKLY")
fi
if [[ ${#LOG_DIRS[@]} -eq 0 ]]; then
  LOG_DIRS=("$SYNTH_DIR/stats")
fi

CSV_OUT="$REPORT_DIR/${WEEK}_team_report.csv"

echo "Aggregating from: ${LOG_DIRS[*]}"

"$PY" "$SYNTH_DIR/collect_stats.py" \
  --logs "${LOG_DIRS[@]}" \
  --group-by developer_id \
  --export "$CSV_OUT"

if $VALIDATE; then
  BASELINE="$SYNTH_DIR/stats/meet-chavda_corpus.jsonl"
  if [[ -f "$BASELINE" ]]; then
    "$PY" "$SYNTH_DIR/run_phase2_validation.py" \
      --baseline-corpus "$BASELINE" \
      --report "$SYNTH_DIR/stats/reports/${WEEK}_phase2_validation.md" \
      || true
  else
    echo "No baseline corpus at $BASELINE — skipping Phase 2 regression"
  fi
fi

echo ""
echo "Team report → $CSV_OUT"
echo "Share CSV + collect_stats stdout with the team."
