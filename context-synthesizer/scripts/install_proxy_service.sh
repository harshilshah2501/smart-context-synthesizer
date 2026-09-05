#!/usr/bin/env bash
# Keep proxy_tool.py running: systemd user unit (Linux/WSL) or LaunchAgent (macOS).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
# shellcheck source=lib/service.sh
source "$SCRIPT_DIR/lib/service.sh"
load_developer_config

chmod +x "${SCRIPT_DIR}/check_proxy_ready.sh"

if ! bash "${SCRIPT_DIR}/check_proxy_ready.sh"; then
  echo "" >&2
  echo "Proxy preflight failed — fix the issue above, then:" >&2
  echo "  bash ${SCRIPT_DIR}/install_proxy_service.sh" >&2
  exit 1
fi

synth_service_install
