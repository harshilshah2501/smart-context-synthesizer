#!/usr/bin/env bash
# Diagnose "proxy running but dashboard shows proxy_requests: 0".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${REPO_ROOT}/context-synthesizer/.env"
PORT="8080"
PROXY_HOST="127.0.0.1"
TELEMETRY_LOG="${REPO_ROOT}/context-synthesizer/stats/telemetry.jsonl"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
PORT="${PROXY_PORT:-8080}"
PROXY_HOST="${PROXY_HOST:-127.0.0.1}"
TELEMETRY_LOG="${TELEMETRY_LOG_PATH:-$TELEMETRY_LOG}"

IS_WSL=0
WSL_IP=""
if [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
  IS_WSL=1
  WSL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

ok()   { echo "  ✓ $*"; }
warn() { echo "  ⚠ $*"; }
fail() { echo "  ✗ $*"; }

read_setting() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "(file missing)"
    return
  fi
  python3 -c "
import json, sys
p = sys.argv[1]
try:
    d = json.loads(open(p).read())
    print(d.get('env', {}).get('ANTHROPIC_BASE_URL', '(not set)'))
except Exception as e:
    print(f'(parse error: {e})')
" "$path" 2>/dev/null || echo "(unreadable)"
}

echo "=== Context Synthesizer — Claude Code routing check ==="
echo ""

# 1. Proxy health
if curl -sf --max-time 3 "http://127.0.0.1:${PORT}/health" >/dev/null; then
  ok "Proxy health OK on WSL 127.0.0.1:${PORT}"
else
  fail "Proxy not responding on 127.0.0.1:${PORT}"
  echo "    systemctl --user status context-synthesizer-proxy"
  exit 1
fi

if [[ "$IS_WSL" -eq 1 && -n "$WSL_IP" ]]; then
  if curl -sf --max-time 3 "http://${WSL_IP}:${PORT}/health" >/dev/null; then
    ok "Proxy reachable on WSL IP ${WSL_IP}:${PORT} (Windows → proxy)"
  else
    warn "Proxy NOT reachable on WSL IP ${WSL_IP}:${PORT}"
    echo "    Ensure PROXY_HOST=0.0.0.0 in ${ENV_FILE} and restart the service."
  fi
fi

echo ""
echo "Claude Code settings (ANTHROPIC_BASE_URL):"

WSL_SETTINGS="${HOME}/.claude/settings.json"
WSL_URL="$(read_setting "$WSL_SETTINGS")"
echo "  WSL (~/.claude/settings.json):     $WSL_URL"
if [[ "$WSL_URL" == *"127.0.0.1:${PORT}"* ]] || [[ "$WSL_URL" == *"localhost:${PORT}"* ]]; then
  ok "WSL settings look correct for Claude Code inside WSL"
elif [[ "$WSL_URL" == "(not set)"* ]] || [[ "$WSL_URL" == "(file missing)" ]]; then
  fail "WSL settings missing — run: bash context-synthesizer/scripts/configure_claude_proxy.sh"
else
  warn "WSL URL unexpected: $WSL_URL (expected http://127.0.0.1:${PORT})"
fi

WIN_SETTINGS=""
if [[ "$IS_WSL" -eq 1 ]]; then
  WIN_USER=""
  if command -v cmd.exe >/dev/null 2>&1; then
    WIN_USER="$(cmd.exe /c 'echo %USERNAME%' 2>/dev/null | tr -d '\r\n' || true)"
  fi
  if [[ -n "$WIN_USER" ]]; then
    WIN_SETTINGS="/mnt/c/Users/${WIN_USER}/.claude/settings.json"
    WIN_URL="$(read_setting "$WIN_SETTINGS")"
    echo "  Windows (%USERPROFILE%\\.claude):  $WIN_URL"
    if [[ -n "$WSL_IP" && "$WIN_URL" == *"${WSL_IP}:${PORT}"* ]]; then
      ok "Windows settings look correct for Claude Code Windows app"
    elif [[ "$WIN_URL" == *"127.0.0.1:${PORT}"* ]]; then
      fail "Windows settings use 127.0.0.1 — that is Windows localhost, NOT the WSL proxy"
      echo "    Fix: bash context-synthesizer/scripts/configure_claude_proxy.sh"
      echo "    Expected: http://${WSL_IP}:${PORT}"
    elif [[ "$WIN_URL" == "(not set)"* ]] || [[ "$WIN_URL" == "(file missing)" ]]; then
      warn "Windows settings missing — if you use Claude Code on Windows, run configure_claude_proxy.sh"
    fi
  fi
fi

read_vscode_base_url() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "(file missing)"
    return
  fi
  python3 -c "
import json, sys
p = sys.argv[1]
try:
    d = json.loads(open(p).read())
    for item in d.get('claudeCode.environmentVariables') or []:
        if isinstance(item, dict) and (item.get('name') or item.get('key')) == 'ANTHROPIC_BASE_URL':
            print(item.get('value') or '(empty)')
            break
    else:
        print('(not set in claudeCode.environmentVariables)')
except Exception as e:
    print(f'(parse error: {e})')
" "$path" 2>/dev/null || echo "(unreadable)"
}

echo ""
echo "VS Code Claude Code extension (claudeCode.environmentVariables):"
VSCODE_CHECKED=0
if [[ -n "${WIN_USER:-}" && -f "/mnt/c/Users/${WIN_USER}/AppData/Roaming/Code/User/settings.json" ]]; then
  VSCODE_PATH="/mnt/c/Users/${WIN_USER}/AppData/Roaming/Code/User/settings.json"
  VSCODE_URL="$(read_vscode_base_url "$VSCODE_PATH")"
  echo "  Windows VS Code:  $VSCODE_URL"
  VSCODE_CHECKED=1
  if [[ -n "$WSL_IP" && "$VSCODE_URL" == *"${WSL_IP}:${PORT}"* ]]; then
    ok "VS Code extension wired to WSL proxy"
  elif [[ "$VSCODE_URL" == *"127.0.0.1:${PORT}"* ]]; then
    fail "VS Code uses 127.0.0.1 — Windows localhost, not WSL proxy"
    echo "    Fix: bash context-synthesizer/scripts/configure_claude_proxy.sh && restart VS Code"
  elif [[ "$VSCODE_URL" == "(not set"* ]] || [[ "$VSCODE_URL" == "(file missing)" ]]; then
    fail "VS Code extension NOT configured — this is required for Claude in VS Code"
    echo "    The extension ignores ~/.claude/settings.json"
    echo "    Fix: bash context-synthesizer/scripts/configure_claude_proxy.sh"
  fi
fi
if [[ -f "$HOME/.config/Code/User/settings.json" ]]; then
  VSCODE_LINUX_URL="$(read_vscode_base_url "$HOME/.config/Code/User/settings.json")"
  echo "  Linux VS Code:    $VSCODE_LINUX_URL"
  VSCODE_CHECKED=1
fi
if [[ "$VSCODE_CHECKED" -eq 0 ]]; then
  warn "No VS Code settings.json found — if using Claude Code in VS Code, run configure_claude_proxy.sh"
fi

echo ""
echo "Recent proxy traffic (journal):"
if command -v journalctl >/dev/null 2>&1; then
  MSG_COUNT="$(journalctl --user -u context-synthesizer-proxy --since "24 hours ago" --no-pager 2>/dev/null | grep -cE 'POST /v1/messages|→ POST /v1/messages' || true)"
  CHAT_COUNT="$(journalctl --user -u context-synthesizer-proxy --since "24 hours ago" --no-pager 2>/dev/null | grep -cE 'POST /v1/chat/completions|→ POST /v1/chat/completions' || true)"
  REJECTED="$(journalctl --user -u context-synthesizer-proxy --since "24 hours ago" --no-pager 2>/dev/null | grep -c 'rejected: no API key' || true)"
  if [[ "$MSG_COUNT" -gt 0 ]]; then
    ok "Claude Code traffic: ${MSG_COUNT} POST /v1/messages in last 24h"
  elif [[ "$CHAT_COUNT" -gt 0 ]]; then
    ok "Cursor/test traffic: ${CHAT_COUNT} POST /v1/chat/completions in last 24h"
  else
    fail "No API traffic in last 24h — only health/dashboard hits"
    echo ""
    echo "  Claude Code in VS Code: extension needs claudeCode.environmentVariables"
    echo "    bash context-synthesizer/scripts/configure_claude_proxy.sh"
    echo "    Restart VS Code, send one message."
    echo ""
    echo "  Live trace while testing:"
    echo "    journalctl --user -u context-synthesizer-proxy -f | grep -E '\\[ACCESS\\]|\\[PROXY\\]'"
  fi
  if [[ "$REJECTED" -gt 0 ]]; then
    warn "${REJECTED} requests reached proxy but were rejected (no API key) — check auth in VS Code env"
  fi
else
  warn "journalctl not available"
fi

echo ""
echo "Telemetry file:"
if [[ -f "$TELEMETRY_LOG" ]]; then
  EVENTS="$(wc -l <"$TELEMETRY_LOG" | tr -d ' ')"
  PROXY_EVENTS="$(grep -c '"source": "proxy"' "$TELEMETRY_LOG" 2>/dev/null || echo 0)"
  echo "  $TELEMETRY_LOG"
  echo "  Lines: $EVENTS  |  proxy events: $PROXY_EVENTS"
  if [[ "$PROXY_EVENTS" -eq 0 ]]; then
    warn "telemetry.jsonl has no proxy events — dashboard will show 0 requests"
  else
    ok "$PROXY_EVENTS proxy events logged"
  fi
else
  warn "No telemetry log yet at $TELEMETRY_LOG (created on first API call)"
fi

echo ""
echo "Done."
