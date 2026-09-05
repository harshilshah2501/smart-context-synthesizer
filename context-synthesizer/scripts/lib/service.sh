#!/usr/bin/env bash
# Proxy process supervisor: systemd --user on Linux/WSL, launchd on macOS.
#
# Source after lib/config.sh. Expects REPO_ROOT when installing the service.

SYNTH_SYSTEMD_UNIT="context-synthesizer-proxy.service"
SYNTH_LAUNCH_LABEL="com.contextsynthesizer.proxy"

synth_is_darwin() {
  [[ "$(uname -s)" == Darwin ]]
}

synth_launch_plist() {
  echo "${HOME}/Library/LaunchAgents/${SYNTH_LAUNCH_LABEL}.plist"
}

synth_launch_target() {
  echo "gui/$(id -u)/${SYNTH_LAUNCH_LABEL}"
}

synth_darwin_log() {
  echo "${HOME}/Library/Logs/context-synthesizer-proxy.log"
}

synth_darwin_err_log() {
  echo "${HOME}/Library/Logs/context-synthesizer-proxy.err.log"
}

# Portable in-file replace (GNU and BSD sed). Usage: synth_replace_line FILE 's/^FOO=.*/FOO=bar/'
synth_replace_line() {
  local file="$1" expr="$2" tmp
  tmp="$(mktemp)"
  sed "$expr" "$file" >"$tmp"
  mv "$tmp" "$file"
}

synth_require_supervisor() {
  if synth_is_darwin; then
    if ! command -v launchctl >/dev/null 2>&1; then
      echo "ERROR: launchctl not found — macOS proxy service requires launchd." >&2
      exit 1
    fi
    return 0
  fi
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "ERROR: systemctl not found — live proxy requires systemd user services (Linux/WSL) or macOS launchd." >&2
    exit 1
  fi
  if ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "" >&2
    echo "ERROR: systemd user session is not available." >&2
    if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
      echo "  WSL: [boot] systemd=true in /etc/wsl.conf, then wsl --shutdown" >&2
    else
      echo "  Ubuntu: loginctl enable-linger \$USER" >&2
    fi
    exit 1
  fi
}

synth_service_is_active() {
  if synth_is_darwin; then
    local pid
    pid="$(launchctl list 2>/dev/null | awk -v l="${SYNTH_LAUNCH_LABEL}" '$3 == l { print $1 }')"
    [[ -n "$pid" && "$pid" != "-" ]]
  else
    systemctl --user is-active --quiet "${SYNTH_SYSTEMD_UNIT}" 2>/dev/null
  fi
}

synth_service_stop() {
  if synth_is_darwin; then
    launchctl bootout "$(synth_launch_target)" 2>/dev/null || true
    launchctl unload "$(synth_launch_plist)" 2>/dev/null || true
  else
    systemctl --user stop "${SYNTH_SYSTEMD_UNIT}" 2>/dev/null || true
  fi
}

synth_service_start() {
  if synth_is_darwin; then
    local plist target
    plist="$(synth_launch_plist)"
    target="$(synth_launch_target)"
    [[ -f "$plist" ]] || return 1
    launchctl bootout "$target" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    launchctl enable "$target" 2>/dev/null || true
    launchctl kickstart -k "$target" 2>/dev/null || true
  else
    systemctl --user enable --now "${SYNTH_SYSTEMD_UNIT}"
  fi
}

synth_service_restart() {
  if synth_is_darwin; then
    if [[ -f "$(synth_launch_plist)" ]]; then
      launchctl kickstart -k "$(synth_launch_target)" 2>/dev/null || synth_service_start
    else
      return 1
    fi
  else
    systemctl --user restart "${SYNTH_SYSTEMD_UNIT}"
  fi
}

synth_service_print_status() {
  if synth_is_darwin; then
    if synth_service_is_active; then
      echo "Proxy service:  running (launchd ${SYNTH_LAUNCH_LABEL})"
    else
      echo "Proxy service:  stopped (launchd ${SYNTH_LAUNCH_LABEL})"
    fi
    if [[ -f "$(synth_launch_plist)" ]]; then
      echo "LaunchAgent:    $(synth_launch_plist)"
    fi
    launchctl print "$(synth_launch_target)" 2>/dev/null | head -n 24 || true
  else
    systemctl --user status context-synthesizer-proxy --no-pager 2>&1 || true
  fi
}

synth_service_logs_follow() {
  if synth_is_darwin; then
    mkdir -p "${HOME}/Library/Logs"
    touch "$(synth_darwin_log)" "$(synth_darwin_err_log)"
    echo "Tailing $(synth_darwin_log) (stderr: $(synth_darwin_err_log))"
    tail -f "$(synth_darwin_log)" "$(synth_darwin_err_log)"
  else
    journalctl --user -u context-synthesizer-proxy -f
  fi
}

synth_service_logs_hint() {
  if synth_is_darwin; then
    echo "  tail -n 40 $(synth_darwin_err_log)"
  else
    echo "  journalctl --user -u context-synthesizer-proxy -n 40 --no-pager"
  fi
}

synth_service_grep_logs() {
  # stdin unused; print matching lines from the last 24h of proxy logs.
  local pattern="$1"
  if synth_is_darwin; then
    local log err
    log="$(synth_darwin_log)"
    err="$(synth_darwin_err_log)"
    [[ -f "$log" ]] && grep -E "$pattern" "$log" 2>/dev/null || true
    [[ -f "$err" ]] && grep -E "$pattern" "$err" 2>/dev/null || true
  else
    journalctl --user -u context-synthesizer-proxy --since "24 hours ago" --no-pager 2>/dev/null | grep -E "$pattern" || true
  fi
}

synth_xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"
  s="${s//</&lt;}"
  s="${s//>/&gt;}"
  printf '%s' "$s"
}

synth_install_launch_agent() {
  local run_proxy="$1" workdir="$2"
  local plist log_out log_err
  plist="$(synth_launch_plist)"
  log_out="$(synth_darwin_log)"
  log_err="$(synth_darwin_err_log)"
  mkdir -p "${HOME}/Library/LaunchAgents" "${HOME}/Library/Logs"
  cat >"$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${SYNTH_LAUNCH_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$(synth_xml_escape "$run_proxy")</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$(synth_xml_escape "$workdir")</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$(synth_xml_escape "$log_out")</string>
  <key>StandardErrorPath</key>
  <string>$(synth_xml_escape "$log_err")</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
</dict>
</plist>
EOF
}

synth_install_systemd_unit() {
  local run_proxy="$1" workdir="$2" env_file="$3"
  local unit_dir unit_file
  unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  unit_file="${unit_dir}/${SYNTH_SYSTEMD_UNIT}"
  mkdir -p "$unit_dir"
  cat >"$unit_file" <<EOF
[Unit]
Description=Context Synthesizer proxy (Claude Code gateway)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${workdir}
EnvironmentFile=-${env_file}
Environment=PYTHONUNBUFFERED=1
ExecStart=${run_proxy}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
}

synth_service_install() {
  local run_proxy workdir env_file port
  run_proxy="${REPO_ROOT}/context-synthesizer/scripts/run_proxy.sh"
  workdir="${REPO_ROOT}/context-synthesizer"
  env_file="${REPO_ROOT}/context-synthesizer/.env"
  chmod +x "$run_proxy"

  synth_service_stop
  if synth_is_darwin; then
    synth_install_launch_agent "$run_proxy" "$workdir"
  else
    synth_install_systemd_unit "$run_proxy" "$workdir" "$env_file"
  fi
  synth_service_start

  port="8080"
  if [[ -f "$env_file" ]]; then
    port="$(grep -E '^PROXY_PORT=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2)"
    port="${port:-8080}"
  fi
  sleep 1
  if synth_service_is_active && curl -sf --max-time 3 "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
    if synth_is_darwin; then
      echo "Proxy service enabled → launchd ${SYNTH_LAUNCH_LABEL} (csynth status)"
    else
      echo "Proxy service enabled → systemctl --user status context-synthesizer-proxy"
    fi
    return 0
  fi
  echo "" >&2
  echo "Proxy failed to stay up. Logs:" >&2
  synth_service_logs_hint >&2
  return 1
}
