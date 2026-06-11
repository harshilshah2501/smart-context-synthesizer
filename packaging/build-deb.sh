#!/usr/bin/env bash
# Build context-synthesizer Ubuntu .deb package
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKG_NAME="context-synthesizer"
VERSION="${VERSION:-0.1.0}"
BUILD_DIR="${ROOT}/packaging/build"
STAGE="${BUILD_DIR}/${PKG_NAME}_${VERSION}_all"

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/usr/lib/context-synthesizer"
mkdir -p "$STAGE/usr/bin"
mkdir -p "$STAGE/etc/context-synthesizer"
mkdir -p "$STAGE/etc/default"
mkdir -p "$STAGE/lib/systemd/system"
mkdir -p "$STAGE/usr/lib/systemd/user"
mkdir -p "$STAGE/var/lib/context-synthesizer/stats"
mkdir -p "$STAGE/usr/share/doc/context-synthesizer"

# Application
install -m 644 "$ROOT/context-synthesizer"/*.py "$STAGE/usr/lib/context-synthesizer/"
install -m 644 "$ROOT/packaging/requirements.txt" "$STAGE/usr/lib/context-synthesizer/"
install -m 644 "$ROOT/context-synthesizer/Claude.md" "$STAGE/etc/context-synthesizer/"

# Docs
install -m 644 "$ROOT/context-synthesizer/Usage.md" "$STAGE/usr/share/doc/context-synthesizer/"
install -m 644 "$ROOT/context-synthesizer/README.md" "$STAGE/usr/share/doc/context-synthesizer/"
install -m 644 "$ROOT/context-synthesizer/CLI_STATS_GUIDE.md" "$STAGE/usr/share/doc/context-synthesizer/"
install -m 644 "$ROOT/packaging/UBUNTU_INSTALL.md" "$STAGE/usr/share/doc/context-synthesizer/"

# Config + systemd
install -m 644 "$ROOT/packaging/context-synthesizer.default" "$STAGE/etc/default/context-synthesizer"
install -m 644 "$ROOT/packaging/context-synthesizer.service" "$STAGE/lib/systemd/system/"
install -m 644 "$ROOT/packaging/context-synthesizer-user.service" "$STAGE/usr/lib/systemd/user/context-synthesizer.service"

# CLI wrappers
install -m 755 "$ROOT/packaging/usr-bin/context-synthesizer-proxy" "$STAGE/usr/bin/"
install -m 755 "$ROOT/packaging/usr-bin/context-synthesizer-collect-stats" "$STAGE/usr/bin/"
install -m 755 "$ROOT/packaging/usr-bin/context-synthesizer-setup-user" "$STAGE/usr/bin/"

# Debian metadata
install -m 644 "$ROOT/packaging/DEBIAN/control" "$STAGE/DEBIAN/"
install -m 644 "$ROOT/packaging/DEBIAN/conffiles" "$STAGE/DEBIAN/"
install -m 755 "$ROOT/packaging/DEBIAN/postinst" "$STAGE/DEBIAN/"
install -m 755 "$ROOT/packaging/DEBIAN/prerm" "$STAGE/DEBIAN/"

# Permissions for runtime (ownership set by dpkg-deb --root-owner-group)
chmod 755 "$STAGE/var/lib/context-synthesizer/stats"

DEB_OUT="${BUILD_DIR}/${PKG_NAME}_${VERSION}_all.deb"
dpkg-deb --root-owner-group --build "$STAGE" "$DEB_OUT"

echo ""
echo "Built: $DEB_OUT"
echo "Install: sudo apt install ./$(basename "$DEB_OUT")"
