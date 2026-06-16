#!/usr/bin/env bash
# Pull latest toolkit tarball from build server → WSL (rsync over SSH).
#
# Setup (once on WSL):
#   1. SSH key: ssh-copy-id harshil@your-build-server
#   2. Config:  mkdir -p ~/.config/context-synthesizer
#               cp bundle-sync.env.example ~/.config/context-synthesizer/bundle-sync.env
#               # edit BUILD_HOST, paths
#   3. Test:    bash fetch-toolkit-bundle.sh
#   4. Cron:    bash fetch-toolkit-bundle.sh --install-cron
#
# On build server: run build-release-tarball.sh (creates context-synthesizer-toolkit-latest.tar.gz)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="${BUNDLE_SYNC_CONF:-$HOME/.config/context-synthesizer/bundle-sync.env}"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/context-synthesizer"
LOG_FILE="${LOG_DIR}/bundle-sync.log"

BUILD_HOST="${BUILD_HOST:-}"
REMOTE_TARBALL="${REMOTE_TARBALL:-}"
LOCAL_DIR="${LOCAL_DIR:-/root/Harshil-PoCs}"
EXTRACT="${EXTRACT:-1}"
PRUNE_OLD="${PRUNE_OLD:-1}"
CRON_SCHEDULE="${CRON_SCHEDULE:-0 */2 * * *}"  # every 2 hours

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  echo "  --install-cron    Add cron job (same schedule as CRON_SCHEDULE in env)"
  echo "  --dry-run         rsync -n only"
  exit "${1:-0}"
}

DRY_RUN=0
INSTALL_CRON=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-cron) INSTALL_CRON=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

if [[ -f "$CONF" ]]; then
  # shellcheck source=bundle-sync.env.example
  source "$CONF"
fi

if [[ "$INSTALL_CRON" -eq 1 ]]; then
  mkdir -p "$LOG_DIR"
  LINE="${CRON_SCHEDULE} ${BASH_SOURCE[0]} >>${LOG_FILE} 2>&1"
  (crontab -l 2>/dev/null | grep -v "fetch-toolkit-bundle.sh" || true; echo "$LINE") | crontab -
  echo "Cron installed: $CRON_SCHEDULE"
  echo "Log: $LOG_FILE"
  exit 0
fi

if [[ -z "$BUILD_HOST" || -z "$REMOTE_TARBALL" ]]; then
  echo "Set BUILD_HOST and REMOTE_TARBALL in $CONF" >&2
  echo "Example: cp ${SCRIPT_DIR}/bundle-sync.env.example $CONF" >&2
  exit 1
fi

mkdir -p "$LOCAL_DIR" "$LOG_DIR"
LOCAL_TARBALL="${LOCAL_DIR}/context-synthesizer-toolkit-latest.tar.gz"

RSYNC_OPTS=(-avz --partial)
[[ "$DRY_RUN" -eq 1 ]] && RSYNC_OPTS+=(-n)

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG_FILE"; }

log "rsync ${BUILD_HOST}:${REMOTE_TARBALL} → ${LOCAL_TARBALL}"
rsync "${RSYNC_OPTS[@]}" "${BUILD_HOST}:${REMOTE_TARBALL}" "$LOCAL_TARBALL"

if [[ "$EXTRACT" != "1" ]]; then
  log "Done (tarball only)."
  exit 0
fi

EXTRACT_DIR="${LOCAL_DIR}/context-synthesizer-toolkit-latest"
TMP="${LOCAL_DIR}/.extract-$$"
rm -rf "$TMP"
mkdir -p "$TMP"
tar -xzf "$LOCAL_TARBALL" -C "$TMP"

EXTRACTED="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
[[ -n "$EXTRACTED" && -d "$EXTRACTED" ]] || { log "ERROR: bad tarball layout"; exit 1; }

if [[ "$PRUNE_OLD" == "1" ]]; then
  find "$LOCAL_DIR" -maxdepth 1 -type d -name 'context-synthesizer-toolkit-*' ! -name 'context-synthesizer-toolkit-latest' -exec rm -rf {} + 2>/dev/null || true
fi

rm -rf "$EXTRACT_DIR"
mv "$EXTRACTED" "$EXTRACT_DIR"
rm -rf "$TMP"

log "Extracted → ${EXTRACT_DIR}"
log "Run: cd ${EXTRACT_DIR} && bash run-setup.sh your.id"
