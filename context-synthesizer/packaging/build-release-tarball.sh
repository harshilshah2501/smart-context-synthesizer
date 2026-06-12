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

# Toolkit + docs + installer (no git, venv, stats, secrets)
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='**/__pycache__' \
  --exclude='context-synthesizer/stats' \
  --exclude='context-synthesizer/*.zip' \
  --exclude='*.jsonl' \
  --exclude='m-coder-core' \
  --exclude='Ollama' \
  --exclude='docs/notes' \
  "$ROOT/install.sh" \
  "$ROOT/context-synthesizer" \
  "$ROOT/docs" \
  "$STAGE/"

mkdir -p "$OUT"
TARBALL="${OUT}/${NAME}.tar.gz"
tar -czf "$TARBALL" -C "$OUT" "$NAME"

echo "Built: $TARBALL"
echo ""
echo "Upload to SharePoint (with install.sh from repo root), then developers run:"
echo "  bash /path/to/OneDrive/.../install.sh --tarball-file /path/to/$(basename "$TARBALL") \\"
echo "    --developer HANDLE --sync-dir '/path/to/.../weekly' --install-cron"
