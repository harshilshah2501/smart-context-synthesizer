#!/usr/bin/env bash
# Context Synthesizer — one-shot installer (no git, no manual config).
#
# Developer:
#   cd context-synthesizer
#   bash install.sh firstname.lastname
#
# Max/Pro subscription only — no API key.
set -euo pipefail

INSTALLER_VERSION="2026.06.23"
DEFAULT_INSTALL_DIR="${HOME}/.local/share/context-synthesizer"

INSTALL_DIR=""
DEVELOPER=""
REINSTALL=0

usage() {
  cat <<EOF
Context Synthesizer — install (Claude Max/Pro, no API key).

  bash run-setup.sh firstname.lastname

Options:
  firstname.lastname     Developer id (optional if Claude CLI is logged in)
  --install-dir PATH     Default: ${DEFAULT_INSTALL_DIR}
  --reinstall            Remove existing install first
  -h, --help
EOF
  exit "${1:-0}"
}

infer_developer_id() {
  if ! command -v claude >/dev/null 2>&1; then
    return 1
  fi
  local email
  email="$(claude auth status 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('email') or '')
except Exception:
    pass
" 2>/dev/null || true)"
  [[ -n "$email" && "$email" == *@* ]] || return 1
  echo "${email%%@*}"
}

build_setup_args() {
  SETUP_ARGS=(--install-dir "$INSTALL_DIR" --developer "$DEVELOPER" --enable-proxy)
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --reinstall) REINSTALL=1; shift ;;
    -h|--help) usage 0 ;;
    --*) echo "Unknown option: $1" >&2; usage 1 ;;
    *)
      if [[ -z "$DEVELOPER" ]]; then
        DEVELOPER="$1"
      else
        echo "Unexpected argument: $1" >&2
        usage 1
      fi
      shift
      ;;
  esac
done

INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

if [[ -z "$DEVELOPER" ]]; then
  DEVELOPER="$(infer_developer_id || true)"
fi
if [[ -z "$DEVELOPER" ]]; then
  echo "Developer id required: bash run-setup.sh firstname.lastname" >&2
  exit 1
fi

stage_flat_repo() {
  local src="$1" dest="$2"
  rm -rf "$dest"
  mkdir -p "$dest/context-synthesizer"
  rsync -a \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='**/__pycache__' \
    --exclude='**/.env' \
    --exclude='stats' \
    --exclude='packaging/build' \
    "$src/" "$dest/context-synthesizer/"
  install -m 755 "$src/install.sh" "$dest/install.sh" 2>/dev/null || cp "$src/install.sh" "$dest/install.sh"
  cp -f "$src/packaging/run-setup.sh" "$dest/run-setup.sh" 2>/dev/null || true
}

INSTALLER_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$INSTALLER_SRC/context-synthesizer/scripts/setup_developer.sh" ]]; then
  echo "=== Context Synthesizer install ==="
  echo "Developer: $DEVELOPER"
  [[ "$REINSTALL" -eq 1 ]] && rm -rf "$INSTALL_DIR"
  if [[ "$INSTALLER_SRC" != "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    cp -a "$INSTALLER_SRC/." "$INSTALL_DIR/"
  fi
  build_setup_args
  exec bash "$INSTALL_DIR/context-synthesizer/scripts/setup_developer.sh" "${SETUP_ARGS[@]}"
fi

if [[ -f "$INSTALLER_SRC/scripts/setup_developer.sh" ]]; then
  echo "=== Context Synthesizer install (dev checkout) ==="
  echo "Developer: $DEVELOPER"
  [[ "$REINSTALL" -eq 1 ]] && rm -rf "$INSTALL_DIR"
  stage_flat_repo "$INSTALLER_SRC" "$INSTALL_DIR"
  build_setup_args
  exec bash "$INSTALL_DIR/context-synthesizer/scripts/setup_developer.sh" "${SETUP_ARGS[@]}"
fi

echo "Invalid package layout — run from context-synthesizer-toolkit-latest/" >&2
exit 1
