#!/usr/bin/env bash
# Context Synthesizer — one-file installer (no git required).
#
# Developers run ONE command (host this file on GitHub raw, shared Drive, or internal CDN):
#
#   curl -fsSL https://raw.githubusercontent.com/harshilshah2501/smart-context-synthesizer/main/install.sh | bash -s -- \
#     --developer YOUR_HANDLE \
#     --rclone-remote 'gdrive:Shared/ContextSynthesizer/weekly' \
#     --enable-proxy \
#     --install-cron
#
# Or from a tarball on shared drive:
#
#   bash install.sh --tarball-file /path/to/context-synthesizer-toolkit.tar.gz --developer YOU ...
#
# Installs to: ~/.local/share/context-synthesizer (override with --install-dir)
set -euo pipefail

INSTALLER_VERSION="1.0.0"
DEFAULT_INSTALL_DIR="${HOME}/.local/share/context-synthesizer"
DEFAULT_GITHUB_REPO="${SYNTH_GITHUB_REPO:-harshilshah2501/smart-context-synthesizer}"
DEFAULT_BRANCH="${SYNTH_GITHUB_BRANCH:-main}"

INSTALL_DIR=""
TARBALL_FILE=""
TARBALL_URL="${SYNTH_TARBALL_URL:-}"
SETUP_ARGS=()

usage() {
  cat <<'EOF'
Context Synthesizer installer (no git clone).

Usage:
  curl -fsSL <install.sh-url> | bash -s -- [options]

Options (passed through to setup):
  --developer HANDLE          Required — unique id (e.g. firstname.lastname)
  --sync-dir PATH             OneDrive local folder (no rclone) — recommended for SharePoint
  --rclone-remote PATH        Optional rclone remote (e.g. gdrive:Shared/...)
  --enable-proxy              Route Claude Code through local synthesizer (live benefit)
  --install-cron              Monday auto-export + upload
  --export-mode d|cursor|a    Default: d (Claude Code Mode D)
  --api-key KEY               Anthropic API key (proxy only; else prompted once)

Installer-only:
  --install-dir PATH          Default: ~/.local/share/context-synthesizer
  --tarball-file PATH         Use local tarball (shared drive) instead of GitHub download
  --tarball-url URL           Download tarball from custom URL
  --reinstall                 Remove existing install dir first
  -h, --help

Environment:
  SYNTH_GITHUB_REPO           Override GitHub repo (owner/name)
  SYNTH_TARBALL_URL           Default tarball URL if not downloading from GitHub
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --tarball-file) TARBALL_FILE="$2"; shift 2 ;;
    --tarball-url) TARBALL_URL="$2"; shift 2 ;;
    --reinstall) INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"; rm -rf "$INSTALL_DIR"; shift ;;
    -h|--help) usage 0 ;;
    *)
      SETUP_ARGS+=("$1")
      if [[ "$1" == --developer || "$1" == --rclone-remote || "$1" == --sync-dir || "$1" == --export-mode || "$1" == --api-key || "$1" == --cursor-project ]]; then
        SETUP_ARGS+=("$2")
        shift
      fi
      shift
      ;;
  esac
done

INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

# Running from a dev checkout? Use current tree (team lead testing).
INSTALLER_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$INSTALLER_SRC/context-synthesizer/scripts/setup_developer.sh" ]]; then
  echo "Using local toolkit at $INSTALLER_SRC"
  exec bash "$INSTALLER_SRC/context-synthesizer/scripts/setup_developer.sh" \
    --install-dir "$INSTALL_DIR" "${SETUP_ARGS[@]}"
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

need_cmd python3
need_cmd tar

mkdir -p "$(dirname "$INSTALL_DIR")"

if [[ ! -f "$INSTALL_DIR/context-synthesizer/scripts/setup_developer.sh" ]]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT

  if [[ -n "$TARBALL_FILE" ]]; then
    echo "Extracting $TARBALL_FILE → $INSTALL_DIR"
    [[ -f "$TARBALL_FILE" ]] || { echo "Tarball not found: $TARBALL_FILE" >&2; exit 1; }
    tar -xzf "$TARBALL_FILE" -C "$TMP"
  else
    if [[ -z "$TARBALL_URL" ]]; then
      TARBALL_URL="https://github.com/${DEFAULT_GITHUB_REPO}/archive/refs/heads/${DEFAULT_BRANCH}.tar.gz"
    fi
    echo "Downloading toolkit v${INSTALLER_VERSION}"
    echo "  from $TARBALL_URL"
    need_cmd curl
    if ! curl -fsSL "$TARBALL_URL" -o "$TMP/archive.tar.gz"; then
      cat >&2 <<'EOF'

Download failed (HTTP 404 often means the GitHub repo is private).

Use SharePoint / OneDrive instead (Motadata):
  1. Team lead uploads install.sh + context-synthesizer-toolkit-*.tar.gz to SharePoint
  2. After OneDrive sync, run:
     bash "/path/to/OneDrive/.../install.sh" \
       --tarball-file "/path/to/context-synthesizer-toolkit-YYYY.MM.DD.tar.gz" \
       --developer YOU --sync-dir "/path/to/.../weekly" --install-cron

Or make the repo public, or use: gh auth login && gh api ... (see DEPLOY.md)
EOF
      exit 1
    fi
    tar -xzf "$TMP/archive.tar.gz" -C "$TMP"
  fi

  EXTRACTED="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
  [[ -n "$EXTRACTED" && -d "$EXTRACTED" ]] || { echo "Invalid tarball layout" >&2; exit 1; }

  rm -rf "$INSTALL_DIR"
  mkdir -p "$INSTALL_DIR"
  # Copy contents (context-synthesizer/, docs/, install.sh)
  cp -a "$EXTRACTED"/. "$INSTALL_DIR/"
  echo "Installed to $INSTALL_DIR"
fi

exec bash "$INSTALL_DIR/context-synthesizer/scripts/setup_developer.sh" \
  --install-dir "$INSTALL_DIR" "${SETUP_ARGS[@]}"
