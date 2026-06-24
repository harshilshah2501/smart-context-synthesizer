#!/usr/bin/env bash
# Developer install — one argument.
#   bash run-setup.sh firstname.lastname
set -euo pipefail
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVELOPER="${1:-}"
[[ -n "$DEVELOPER" ]] || { echo "Usage: bash run-setup.sh firstname.lastname" >&2; exit 1; }
exec bash "$PKG_DIR/install.sh" "$DEVELOPER"
