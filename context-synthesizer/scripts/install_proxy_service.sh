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

cat >"$UNIT_FILE" <<EOF
[Unit]
Description=Context Synthesizer proxy (Claude Code gateway)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=-${ENV_FILE}
ExecStart=${REPO_ROOT}/.venv/bin/python ${REPO_ROOT}/context-synthesizer/proxy_tool.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now context-synthesizer-proxy.service
echo "Proxy service enabled → systemctl --user status context-synthesizer-proxy"
