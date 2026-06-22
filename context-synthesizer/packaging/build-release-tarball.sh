#!/usr/bin/env bash
# Build a distributable tarball for shared drive (developers run install.sh --tarball-file).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${VERSION:-$(date +%Y.%m.%d)}"
OUT="${ROOT}/context-synthesizer/packaging/build"
NAME="context-synthesizer-toolkit-${VERSION}"
STAGE="${OUT}/${NAME}"

rm -rf "$STAGE"
mkdir -p "$STAGE"

ENV_FILE="$ROOT/context-synthesizer/.env"
if [[ -f "$ENV_FILE" ]] && grep -qE '^ANTHROPIC_API_KEY=.' "$ENV_FILE" 2>/dev/null; then
  echo "ERROR: $ENV_FILE contains ANTHROPIC_API_KEY — remove it before building." >&2
  echo "  Max/Pro rollout: no team API key in the package." >&2
  exit 1
fi

# Toolkit + docs + installer (no git, venv, stats, secrets)
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='**/__pycache__' \
  --exclude='**/.env' \
  --exclude='context-synthesizer/stats' \
  --exclude='context-synthesizer/packaging/build' \
  --exclude='context-synthesizer/*.zip' \
  --exclude='*.jsonl' \
  --exclude='m-coder-core' \
  --exclude='Ollama' \
  --exclude='docs/notes' \
  "$ROOT/install.sh" \
  "$ROOT/context-synthesizer" \
  "$ROOT/docs" \
  "$STAGE/"

install -m 644 "$ROOT/context-synthesizer/packaging/INSTALL.txt" "$STAGE/"
install -m 755 "$ROOT/context-synthesizer/packaging/run-setup.sh" "$STAGE/"
install -m 644 "$ROOT/context-synthesizer/packaging/team.conf.example" "$STAGE/"
cat >"$STAGE/team.conf" <<'EOF'
# Team lead: set SYNC_DIR to your synced weekly folder.
SYNC_DIR="$HOME/OneDrive - Motadata/ContextSynthesizer/weekly"
# Primary: live compaction via local proxy (Claude Code Max/Pro login).
ENABLE_PROXY=1
# Optional: Monday corpus export to SharePoint for team rollup.
ENABLE_WEEKLY_CRON=1
EXTRA_SETUP_ARGS=()
EOF

mkdir -p "$OUT"
TARBALL="${OUT}/${NAME}.tar.gz"
tar -czf "$TARBALL" -C "$OUT" "$NAME"
ln -sfn "$(basename "$TARBALL")" "${OUT}/context-synthesizer-toolkit-latest.tar.gz"

echo "Built: $TARBALL"
echo "Latest: ${OUT}/context-synthesizer-toolkit-latest.tar.gz → $(basename "$TARBALL")"
echo ""
echo "Share on SharePoint:"
echo "  Option A — upload $(basename "$TARBALL") (devs extract after sync)"
echo "  Option B — upload extracted folder $NAME/ (devs sync folder as-is)"
echo ""
echo "Team lead: edit team.conf (SYNC_DIR) in the package once."
echo "Developer: bash run-setup.sh firstname.lastname"
echo "Dashboard:  bash context-synthesizer/scripts/open_dashboard.sh"
echo "            (WSL: use WSL IP URL in Windows browser — see docs/guides/DASHBOARD.md)"
