#!/usr/bin/env bash
# Build a distributable tarball for SharePoint / one-shot install.sh.
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
  "$REPO_ROOT/packaging/team.conf.example" \
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
  --exclude='packaging/team.conf.example' \
  "$REPO_ROOT/" "$STAGE/context-synthesizer/"

cat >"$STAGE/team.conf" <<'EOF'
# Team lead: bash packaging/publish-to-sharepoint.sh (not used by developers)
ENABLE_PROXY=1
EXTRA_SETUP_ARGS=()
EOF

install -m 644 "$REPO_ROOT/packaging/share.conf" "$STAGE/packaging/share.conf" 2>/dev/null || \
  mkdir -p "$STAGE/packaging" && cp "$REPO_ROOT/packaging/share.conf" "$STAGE/packaging/"
install -m 755 "$REPO_ROOT/packaging/publish-to-sharepoint.sh" "$STAGE/packaging/" 2>/dev/null || true

mkdir -p "$OUT"
TARBALL="${OUT}/${NAME}.tar.gz"
tar -czf "$TARBALL" -C "$OUT" "$NAME"
ln -sfn "$(basename "$TARBALL")" "${OUT}/context-synthesizer-toolkit-latest.tar.gz"

echo "Built: $TARBALL"
echo ""
echo "Team lead — publish to SharePoint (OneDrive sync):"
echo "  bash packaging/publish-to-sharepoint.sh"
echo ""
echo "Developer (Ubuntu) — after downloading/syncing from SharePoint:"
echo '  cd context-synthesizer-toolkit-latest && bash run-setup.sh firstname.lastname'
