#!/usr/bin/env bash
# Build a distributable tarball for one-shot install (no git required).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-$(date +%Y.%m.%d)}"
OUT="${REPO_ROOT}/packaging/build"
NAME="context-synthesizer-toolkit-${VERSION}"
STAGE="${OUT}/${NAME}"

rm -rf "$STAGE"
mkdir -p "$STAGE"

ENV_FILE="$REPO_ROOT/.env"
if [[ -f "$ENV_FILE" ]] && grep -qE '^ANTHROPIC_API_KEY=.' "$ENV_FILE" 2>/dev/null; then
  echo "ERROR: $ENV_FILE contains ANTHROPIC_API_KEY — remove it before building." >&2
  exit 1
fi

# Repo root is the toolkit (install.sh + context-synthesizer package layout)
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='**/__pycache__' \
  --exclude='**/.env' \
  --exclude='stats' \
  --exclude='packaging/build' \
  --exclude='*.zip' \
  --exclude='*.jsonl' \
  "$REPO_ROOT/install.sh" \
  "$REPO_ROOT/packaging/run-setup.sh" \
  "$REPO_ROOT/packaging/INSTALL.txt" \
  "$STAGE/"
[[ -d "$REPO_ROOT/docs" ]] && rsync -a "$REPO_ROOT/docs" "$STAGE/"
if [[ ! -d "$STAGE/docs" && -d "$REPO_ROOT/../docs" ]]; then
  rsync -a "$REPO_ROOT/../docs" "$STAGE/"
fi

# Nested package (scripts expect REPO_ROOT/context-synthesizer/...)
mkdir -p "$STAGE/context-synthesizer"
rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='**/__pycache__' \
  --exclude='**/.env' \
  --exclude='stats' \
  --exclude='packaging/build' \
  --exclude='*.zip' \
  --exclude='*.jsonl' \
  --exclude='docs' \
  --exclude='install.sh' \
  --exclude='packaging/run-setup.sh' \
  --exclude='packaging/INSTALL.txt' \
  "$REPO_ROOT/" "$STAGE/context-synthesizer/"

mkdir -p "$OUT"
TARBALL="${OUT}/${NAME}.tar.gz"
tar -czf "$TARBALL" -C "$OUT" "$NAME"
ln -sfn "$(basename "$TARBALL")" "${OUT}/context-synthesizer-toolkit-latest.tar.gz"

echo "Built: $TARBALL"
echo ""
echo "Users:"
echo '  tar -xzf context-synthesizer-toolkit-*.tar.gz'
echo '  cd context-synthesizer-toolkit-* && bash run-setup.sh firstname.lastname'
