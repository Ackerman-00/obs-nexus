#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

SPEC_FILE="hermes-agent-desktop.spec"
COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
BASE_VER=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
GIT_DATE=$(grep -E "^%global gitdate" "$SPEC_FILE" | awk '{print $3}')
SHORT=$(grep -E "^%global shortcommit" "$SPEC_FILE" | awk '{print $3}')
VERSION="$BASE_VER+git$GIT_DATE.$SHORT"
OUT="hermes-agent-desktop-$VERSION.tar.gz"
NODE_URL="https://nodejs.org/download/release/v26.12.1/node-v26.12.1-linux-x64.tar.xz"
NODE_SHA256="6170b2d474e1c626f43cff3adc118df9fe3b573258a4fc3d850c8dbc6b079bbd"
PNPM_URL="https://registry.npmjs.org/@pnpm/exe.linux-x64/-/exe.linux-x64-12.15.0.tgz"
PNPM_SHA256="402f7045b1e0587acb1542f18d38afbccb6babf3c7451394e6fb3d9f0160c6ca"

if ! command -v docker >/dev/null 2>&1; then
    echo "docker not available; payload build is CI-only - skipping."
    exit 0
fi

TXDIR=$(mktemp -d)
trap 'rm -rf "$TXDIR"' EXIT
echo "Downloading upstream source at $COMMIT..."
curl -fsSL --retry 3 --connect-timeout 60 "https://github.com/NousResearch/hermes-agent/archive/$COMMIT.tar.gz" -o "$TXDIR/main.tar.gz"
tar -xzf "$TXDIR/main.tar.gz" -C "$TXDIR"
SRC="$TXDIR/hermes-agent-$COMMIT"
[ -d "$SRC" ] || { echo "unexpected source layout; aborting" >&2; exit 1; }

mkdir -p "$TXDIR/tools/node" "$TXDIR/tools/pnpm"
curl -fsSL --retry 3 --connect-timeout 120 "$NODE_URL" -o "$TXDIR/node.tar.xz"
echo "$NODE_SHA256  $TXDIR/node.tar.xz" | sha256sum -c --status
tar -xJf "$TXDIR/node.tar.xz" -C "$TXDIR/tools/node" --strip-components=1
curl -fsSL --retry 3 --connect-timeout 120 "$PNPM_URL" -o "$TXDIR/pnpm.tgz"
echo "$PNPM_SHA256  $TXDIR/pnpm.tgz" | sha256sum -c --status
tar -xzf "$TXDIR/pnpm.tgz" -C "$TXDIR/tools/pnpm"

echo "Building hermes-agent-desktop in fedora container..."
docker run --rm -v "$TXDIR":/work -w /work fedora:latest bash -ec "
  dnf install -y --quiet git curl xz zstd make gcc-c++ python3 libX11-devel libXi-devel libatomic &&
  export PATH=\"/work/tools/node/bin:/work/tools/pnpm/package:\$PATH\" &&
  node --version && pnpm --version &&
  cd '/work/hermes-agent-$COMMIT' &&
  export CI=true PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 ELECTRON_SKIP_BINARY_DOWNLOAD=0 &&
  pnpm install --frozen-lockfile &&
  pnpm --filter hermes run build &&
  node scripts/build/electron-runtime.mjs --source . &&
  cd apps/desktop &&
  node scripts/run-electron-builder.mjs --linux --x64 --dir --publish never
"

PAYLOAD="$SRC/apps/desktop/release/linux-unpacked"
[ -d "$PAYLOAD" ] || { echo "electron-builder did not produce release/linux-unpacked" >&2; exit 1; }
[ -x "$PAYLOAD/Hermes" ] || { echo "linux-unpacked has no Hermes binary" >&2; exit 1; }
[ -f "$PAYLOAD/resources/app.asar" ] || { echo "linux-unpacked has no app.asar" >&2; exit 1; }

STAGE="$TXDIR/stage"
mkdir -p "$STAGE/hermes-agent-desktop-$VERSION"
cp -a "$PAYLOAD" "$STAGE/hermes-agent-desktop-$VERSION/linux-unpacked"
cp "$SRC/LICENSE" "$STAGE/hermes-agent-desktop-$VERSION/LICENSE"

for old in hermes-agent-desktop-*.tar.gz; do
    [ "$old" = "$OUT" ] || rm -f "$old"
done
tar -czf "$OUT" -C "$STAGE" "hermes-agent-desktop-$VERSION"
ls -l "$OUT"
echo "Payload sha256: $(sha256sum "$OUT" | awk '{print $1}')"
