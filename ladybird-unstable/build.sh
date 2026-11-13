#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

SPEC_FILE="ladybird-unstable.spec"
COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
BASE_VER=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
GIT_DATE=$(grep -E "^%global gitdate" "$SPEC_FILE" | awk '{print $3}')
SHORT=$(grep -E "^%global shortcommit" "$SPEC_FILE" | awk '{print $3}')
VERSION="$BASE_VER+git$GIT_DATE.$SHORT"
OUT="ladybird-unstable-$VERSION.tar.gz"
VCPKG_OVERRIDES=""

if ! command -v docker >/dev/null 2>&1; then
    echo "docker not available; payload build is CI-only - skipping."
    exit 0
fi

TXDIR=$(mktemp -d)
trap 'rm -rf "$TXDIR"' EXIT
cp "$PWD/check-bundled-libs.py" "$TXDIR/check-bundled-libs.py"
echo "Downloading upstream source at $COMMIT..."
curl -fsSL --retry 3 --connect-timeout 60 "https://github.com/LadybirdBrowser/ladybird/archive/$COMMIT.tar.gz" -o "$TXDIR/main.tar.gz"
tar -xzf "$TXDIR/main.tar.gz" -C "$TXDIR"
SRC="$TXDIR/ladybird-$COMMIT"
[ -d "$SRC" ] || { echo "unexpected source layout; aborting" >&2; exit 1; }
cp "$SRC/LICENSE" "$TXDIR/LICENSE"

echo "Building ladybird in fedora container (this takes a long time)..."
NPROC=$(nproc)
docker run --rm -e NPROC="$NPROC" -v "$TXDIR":/work -w /work fedora:latest bash -ec "
  dnf install -y --quiet \
    git curl tar xz zstd unzip zip make lld nasm patch patchelf perl pkgconf-pkg-config \
    python3 rust cargo gcc gcc-c++ cmake ninja-build \
    qt6-qtbase-devel qt6-qtbase-private-devel qt6-positioning-devel qt6-tools-devel qt6-wayland-devel \
    glslang-devel libdrm-devel libglvnd-devel libpulse-devel liberation-fonts \
    ncurses-devel wayland-devel xcb-util-wm-devel &&
  QT_VER=\$(qmake6 -query QT_VERSION 2>/dev/null || qmake-qt6 -query QT_VERSION 2>/dev/null || echo unknown) &&
  echo \"system Qt version: \$QT_VER\" &&
  python3 -c \"import sys; v='\$QT_VER'.split('.'); sys.exit(0 if v and v[0]=='6' and int(v[1])>=10 else 1)\" || { echo 'ERROR: system Qt below 6.10; ladybird cannot build against it' >&2; exit 1; } &&
  cd '/work/ladybird-$COMMIT' &&
  export VCPKG_FORCE_SYSTEM_BINARIES=1 &&
  python3 Meta/ladybird.py vcpkg --preset Release &&
  cmake --preset Release -S . -B Build/release -DBUILD_TESTING=OFF -DENABLE_INSTALL_FREEDESKTOP_FILES=OFF -DCMAKE_INSTALL_PREFIX=/opt/ladybird -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=OFF -DENABLE_CI_BASELINE_CPU=ON &&
  if grep -q -- '-march=native' Build/release/build.ninja; then echo 'ERROR: -march=native leaked into the build' >&2; exit 1; fi &&
  cmake --build Build/release --parallel "$NPROC" &&
  DESTDIR=/work/payload cmake --install Build/release --component ladybird_Runtime &&
  DESTDIR=/work/payload cmake --install Build/release --component Lagom_Runtime &&
  DESTDIR=/work/payload cmake --install Build/release --component ladybird_SystemIntegration &&
  mkdir -p /work/payload/opt/ladybird/lib64 &&
  VCPKG_LIBS=\\\$(find Build/release/vcpkg_installed/*-linux-dynamic/lib -maxdepth 1 -name '*.so*' -print) &&
  test -n \"\\\$VCPKG_LIBS\" &&
  cp -a \\\$VCPKG_LIBS /work/payload/opt/ladybird/lib64/ &&
  chmod -R u+w /work/payload/opt/ladybird &&
  rm -f /work/payload/opt/ladybird/lib64/libicu*.so* &&
  python3 /work/check-bundled-libs.py /work/payload/opt/ladybird/lib64
"

mkdir -p "$TXDIR/stage/ladybird-unstable-$VERSION"
cp -a "$TXDIR/payload/opt" "$TXDIR/stage/ladybird-unstable-$VERSION/"
mkdir -p "$TXDIR/stage/ladybird-unstable-$VERSION/usr"
for f in bin share; do
  [ -e "$TXDIR/payload/usr/$f" ] && cp -a "$TXDIR/payload/usr/$f" "$TXDIR/stage/ladybird-unstable-$VERSION/usr/"
done
cp "$TXDIR/LICENSE" "$TXDIR/stage/ladybird-unstable-$VERSION/"

for old in ladybird-unstable-*.tar.gz; do
    [ "$old" = "$OUT" ] || rm -f "$old"
done
tar -czf "$OUT" -C "$TXDIR/stage" "ladybird-unstable-$VERSION"
ls -l "$OUT"
echo "Payload sha256: $(sha256sum "$OUT" | awk '{print $1}')"
