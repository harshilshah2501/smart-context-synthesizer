#!/usr/bin/env bash
# systemd user service: keep proxy_tool.py running (live compaction benefit).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
load_developer_config

UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_FILE="$UNIT_DIR/context-synthesizer-proxy.service"
ENV_FILE="$REPO_ROOT/context-synthesizer/.env"

mkdir -p "$UNIT_DIR"

# API key optional at install: Claude Code forwards x-api-key per request (Max/Pro login).
# Optional fallback: ANTHROPIC_API_KEY in context-synthesizer/.env for non-CLI clients.

RUN_PROXY="${REPO_ROOT}/context-synthesizer/scripts/run_proxy.sh"
chmod +x "$RUN_PROXY" "${SCRIPT_DIR}/check_proxy_ready.sh"

systemctl --user stop context-synthesizer-proxy.service 2>/dev/null || true

if ! bash "${SCRIPT_DIR}/check_proxy_ready.sh"; then
  echo "" >&2
  echo "Proxy preflight failed — fix the issue above, then:" >&2
  echo "  bash ${SCRIPT_DIR}/install_proxy_service.sh" >&2
  exit 1
fi

cat >"$UNIT_FILE" <<EOF
[Unit]
Description=Context Synthesizer proxy (Claude Code gateway)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}/context-synthesizer
EnvironmentFile=-${ENV_FILE}
ExecStart=${RUN_PROXY}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now context-synthesizer-proxy.service
sleep 1
if ! systemctl --user is-active --quiet context-synthesizer-proxy.service; then
  echo "" >&2
  echo "Proxy failed to stay up. Logs:" >&2
  echo "  journalctl --user -u context-synthesizer-proxy -n 40 --no-pager" >&2
  systemctl --user status context-synthesizer-proxy.service --no-pager >&2 || true
  exit 1
fi
echo "Proxy service enabled → systemctl --user status context-synthesizer-proxy"
