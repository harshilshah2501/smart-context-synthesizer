#!/usr/bin/env bash
# Smoke test for lib/service.sh — no proxy start, safe in CI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/service.sh
source "$SCRIPT_DIR/lib/service.sh"

os="$(uname -s)"
if [[ "$os" == Darwin ]]; then
  synth_is_darwin
else
  if synth_is_darwin; then
    echo "synth_is_darwin true on $os" >&2
    exit 1
  fi
fi

[[ "$(synth_xml_escape 'a&b<c>')" == 'a&amp;b&lt;c&gt;' ]]

echo "test_service_lib: OK ($os)"
