#!/usr/bin/env bash
# Developer entry point — run from the shared package folder (after OneDrive sync).
#
# Team lead: edit team.conf once (sync folder path).
# Developer: bash run-setup.sh firstname.lastname
set -euo pipefail

PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVELOPER="${1:-}"

if [[ -z "$DEVELOPER" ]]; then
  echo "Usage: bash run-setup.sh <your-id>" >&2
  echo "  Example: bash run-setup.sh harshil.shah" >&2
  exit 1
fi

CONF="$PKG_DIR/team.conf"
if [[ ! -f "$CONF" ]]; then
  echo "Missing team.conf — team lead should copy team.conf.example → team.conf and set SYNC_DIR" >&2
  exit 1
fi
# shellcheck source=team.conf.example
source "$CONF"

if [[ -z "${SYNC_DIR:-}" ]]; then
  echo "SYNC_DIR not set in team.conf" >&2
  exit 1
fi

# Live compaction (proxy) is the primary benefit; weekly cron is optional telemetry.
ENABLE_PROXY="${ENABLE_PROXY:-1}"
ENABLE_WEEKLY_CRON="${ENABLE_WEEKLY_CRON:-1}"

ARGS=(--developer "$DEVELOPER" --sync-dir "$SYNC_DIR")
[[ "$ENABLE_PROXY" == 1 ]] && ARGS+=(--enable-proxy)
[[ "$ENABLE_WEEKLY_CRON" == 1 ]] && ARGS+=(--install-cron)
if [[ -n "${EXTRA_SETUP_ARGS+x}" && ${#EXTRA_SETUP_ARGS[@]} -gt 0 ]]; then
  ARGS+=("${EXTRA_SETUP_ARGS[@]}")
fi
exec bash "$PKG_DIR/install.sh" "${ARGS[@]}"
