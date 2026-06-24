#!/usr/bin/env bash
# Build toolkit and copy to the synced OneDrive folder → SharePoint auto-updates.
#
# Team lead (WSL or Git Bash on Windows):
#   bash packaging/publish-to-sharepoint.sh
#
# No install.sh edits per release. Developers always use:
#   .../Context-Synthesizer/context-synthesizer-toolkit-latest/
#   bash run-setup.sh firstname.lastname
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONF="$SCRIPT_DIR/share.conf"
if [[ ! -f "$CONF" ]]; then
  echo "Missing $CONF" >&2
  echo "  cp packaging/share.conf.example packaging/share.conf" >&2
  echo "  # edit paths, then re-run" >&2
  exit 1
fi
# shellcheck source=share.conf
source "$CONF"

_resolve_share_dir() {
  if [[ -d "${SHARE_DIR_WSL:-}" ]]; then
    echo "$SHARE_DIR_WSL"
    return
  fi
  if [[ -n "${SHARE_DIR_WIN:-}" ]]; then
    local wsl_path
    wsl_path="$(wslpath -u "$SHARE_DIR_WIN" 2>/dev/null || true)"
    if [[ -n "$wsl_path" && -d "$wsl_path" ]]; then
      echo "$wsl_path"
      return
    fi
  fi
  if [[ -d "${SHARE_DIR_WIN:-}" ]]; then
    echo "$SHARE_DIR_WIN"
    return
  fi
  return 1
}

SHARE_DIR="$(_resolve_share_dir || true)"
if [[ -z "$SHARE_DIR" ]]; then
  echo "Share folder not found." >&2
  echo "  WSL:  ${SHARE_DIR_WSL:-<unset>}" >&2
  echo "  Win:  ${SHARE_DIR_WIN:-<unset>}" >&2
  echo "Create it in OneDrive or fix packaging/share.conf" >&2
  exit 1
fi

LATEST_NAME="${LATEST_NAME:-context-synthesizer-toolkit-latest}"

echo "=== Build ==="
bash "$SCRIPT_DIR/build-release-tarball.sh"

VERSION="$(date +%Y.%m.%d)"
BUILD_DIR="$REPO_ROOT/packaging/build"
STAMPED="$BUILD_DIR/context-synthesizer-toolkit-${VERSION}"
TARBALL="$BUILD_DIR/context-synthesizer-toolkit-${VERSION}.tar.gz"
LATEST_LINK="$BUILD_DIR/context-synthesizer-toolkit-latest.tar.gz"

# build-release-tarball may use VERSION from env; find newest stamped dir
if [[ ! -d "$STAMPED" ]]; then
  STAMPED="$(find "$BUILD_DIR" -maxdepth 1 -type d -name 'context-synthesizer-toolkit-*' ! -name '*latest*' | sort | tail -1)"
fi
if [[ ! -f "$TARBALL" ]]; then
  TARBALL="$(find "$BUILD_DIR" -maxdepth 1 -name 'context-synthesizer-toolkit-*.tar.gz' ! -name '*latest*' | sort | tail -1)"
fi
[[ -d "$STAMPED" ]] || { echo "Build output missing under $BUILD_DIR" >&2; exit 1; }
[[ -f "$TARBALL" ]] || { echo "Tarball missing under $BUILD_DIR" >&2; exit 1; }

DEST_LATEST="$SHARE_DIR/$LATEST_NAME"
DEST_TARBALL="$SHARE_DIR/$(basename "$TARBALL")"

echo ""
echo "=== Publish → OneDrive (SharePoint sync) ==="
echo "  Share:  $SHARE_DIR"
echo "  Latest: $DEST_LATEST"
echo "  Archive: $DEST_TARBALL"

mkdir -p "$SHARE_DIR"
rm -rf "$DEST_LATEST"
cp -a "$STAMPED" "$DEST_LATEST"
cp -f "$TARBALL" "$DEST_TARBALL"
[[ -L "$LATEST_LINK" ]] && cp -f "$LATEST_LINK" "$SHARE_DIR/context-synthesizer-toolkit-latest.tar.gz" 2>/dev/null || \
  cp -f "$TARBALL" "$SHARE_DIR/context-synthesizer-toolkit-latest.tar.gz"

cat >"$SHARE_DIR/INSTALL.txt" <<EOF
Context Synthesizer — Motadata team install
===========================================

Ubuntu 22.04 — pick one way to get the toolkit:

  A) Sync this SharePoint/OneDrive folder (recommended)
     cd context-synthesizer-toolkit-latest

  B) Download and extract the .tar.gz archive
     tar -xzf context-synthesizer-toolkit-*.tar.gz
     cd context-synthesizer-toolkit-*

Then:
  bash run-setup.sh firstname.lastname

Example:
  bash run-setup.sh harshil.shah

Verify:
  csynth doctor
  csynth dashboard

Toggle proxy (no reinstall):
  csynth proxy on | csynth proxy off

Claude Max/Pro login only — no API key.

Package updated: $(date -Iseconds)
EOF

echo ""
echo "Done. OneDrive will sync to SharePoint."
echo ""
echo "Tell developers:"
echo "  1. Open SharePoint → Sync or download context-synthesizer-toolkit-latest"
echo "  2. bash run-setup.sh <azure-email-local-part>"
