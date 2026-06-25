#!/usr/bin/env bash
# Upgrade an installed Context Synthesizer toolkit in place.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"

load_developer_config

GITHUB_REPO="${SYNTH_GITHUB_REPO:-harshilshah2501/smart-context-synthesizer}"
GITHUB_BRANCH="${SYNTH_GITHUB_BRANCH:-main}"
PY="${REPO_ROOT}/.venv/bin/python"
VENV="${REPO_ROOT}/.venv"
PKG="${REPO_ROOT}/context-synthesizer"
ENV_FILE="${PKG}/.env"

echo "=== Context Synthesizer upgrade ==="
echo "Install root: $REPO_ROOT"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [[ -d "$REPO_ROOT/.git" ]]; then
  echo "Pulling git checkout..."
  git -C "$REPO_ROOT" fetch origin "$GITHUB_BRANCH"
  git -C "$REPO_ROOT" merge --ff-only "origin/$GITHUB_BRANCH"
else
  ARCHIVE_URL="https://github.com/${GITHUB_REPO}/archive/refs/heads/${GITHUB_BRANCH}.tar.gz"
  echo "Downloading $ARCHIVE_URL"
  curl -fsSL "$ARCHIVE_URL" -o "$TMP/archive.tar.gz"
  tar -xzf "$TMP/archive.tar.gz" -C "$TMP"
  EXTRACTED="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
  [[ -n "$EXTRACTED" ]] || { echo "Invalid archive layout" >&2; exit 1; }
  echo "Syncing package (preserving .env and stats/)..."
  rsync -a \
    --exclude='.env' \
    --exclude='stats' \
    --exclude='.venv' \
    "$EXTRACTED/context-synthesizer/" "$PKG/"
  rsync -a \
    --exclude='.git' \
    "$EXTRACTED/docs" "$REPO_ROOT/" 2>/dev/null || true
  [[ -f "$EXTRACTED/install.sh" ]] && install -m 755 "$EXTRACTED/install.sh" "$REPO_ROOT/install.sh"
fi

if [[ ! -x "$PY" ]]; then
  echo "Creating venv..."
  python3 -m venv "$VENV"
fi

"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -r "$PKG/requirements.txt"

install -m 755 "$PKG/scripts/csynth" "${HOME}/.local/bin/csynth"

if [[ "${ENABLE_PROXY:-0}" == "1" ]] && command -v systemctl >/dev/null 2>&1; then
  echo "Restarting proxy..."
  systemctl --user restart context-synthesizer-proxy
fi

echo ""
echo "Upgrade complete."
echo "  csynth doctor"
if [[ -f "$ENV_FILE" ]]; then
  echo "  (preserved $ENV_FILE)"
fi
