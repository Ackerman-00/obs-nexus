#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="ghostty.spec"
CHANGES_FILE="ghostty.changes"
GITHUB_REPO="ghostty-org/ghostty"
ZIG_VER="0.15.2"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "🔍 Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)

if [ -z "$LATEST_TAG" ]; then
    echo "  -> ❌ [ERROR] Failed to fetch latest tag."
    exit 1
fi

LATEST_VERSION="${LATEST_TAG#v}"

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

fetch_vendor_cache() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://release.files.ghostty.org/$ver/ghostty-$ver.tar.gz" \
        -o "$tmpd/upstream.tar.gz" \
        || { echo "source tarball download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -xzf "$tmpd/upstream.tar.gz" -C "$tmpd" \
        || { echo "source tarball corrupt."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://ziglang.org/download/$ZIG_VER/zig-x86_64-linux-$ZIG_VER.tar.xz" \
        -o "$tmpd/zig.tar.xz" \
        || { echo "zig download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -xJf "$tmpd/zig.tar.xz" -C "$tmpd" \
        || { echo "zig tarball corrupt."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    local srcdir="$tmpd/ghostty-$ver"
    [ -f "$srcdir/build.zig.zon.txt" ] \
        || { echo "build.zig.zon.txt missing in $ver tarball."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mkdir -p "$srcdir/vendor/zig"
    export ZIG_GLOBAL_CACHE_DIR="$srcdir/vendor/zig"
    while IFS= read -r url; do
        [ -z "$url" ] && continue
        "$tmpd/zig-x86_64-linux-$ZIG_VER/zig" fetch "$url" >/dev/null 2>&1 \
            || { echo "zig fetch failed: $url"; trap - EXIT; rm -rf "$tmpd"; return 1; }
    done < "$srcdir/build.zig.zon.txt"
    unset ZIG_GLOBAL_CACHE_DIR
    find "$srcdir/vendor/zig" -type d -iname test -print0 | xargs -r0 rm -rf
    tar --zstd -cf "vendor.tar.zst" -C "$srcdir" vendor/zig \
        || { echo "vendor pack failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    ls -l "vendor.tar.zst"
    trap - EXIT
    rm -rf "$tmpd"
}

assemble_wrapper() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    for f in "ghostty-$ver.tar.gz" "vendor.tar.zst" "zig-x86_64-linux-$ZIG_VER.tar.xz"; do
        [ -f "$f" ] || { echo "wrapper input missing: $f"; trap - EXIT; rm -rf "$tmpd"; return 1; }
    done
    mkdir -p "$tmpd/stage/ghostty-$ver"
    tar -xzf "ghostty-$ver.tar.gz" -C "$tmpd/stage/ghostty-$ver" --strip-components=1 \
        || { echo "source extract failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mkdir -p "$tmpd/stage/ghostty-$ver/vendor"
    tar --zstd -xf "vendor.tar.zst" -C "$tmpd/stage/ghostty-$ver/vendor" --strip-components=1 \
        || { echo "vendor extract failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mkdir -p "$tmpd/stage/ghostty-$ver/zig"
    tar -xJf "zig-x86_64-linux-$ZIG_VER.tar.xz" -C "$tmpd/stage/ghostty-$ver/zig" --strip-components=1 \
        || { echo "zig extract failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    [ -x "$tmpd/stage/ghostty-$ver/zig/zig" ] \
        && { [ -f "$tmpd/stage/ghostty-$ver/build.zig" ] || [ -f "$tmpd/stage/ghostty-$ver/src/build.zig" ]; } \
        || { echo "wrapper layout broken."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "ghostty-$ver-debian.tar.gz" -C "$tmpd/stage" "ghostty-$ver" \
        || { echo "wrapper pack failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    ls -l "ghostty-$ver-debian.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

if [ ! -f "zig-x86_64-linux-$ZIG_VER.tar.xz" ]; then
    echo "  -> Zig compiler blob missing locally; rebuilding..."
    curl -fsSL --retry 3 \
        "https://ziglang.org/download/$ZIG_VER/zig-x86_64-linux-$ZIG_VER.tar.xz" \
        -o "zig-x86_64-linux-$ZIG_VER.tar.xz" || \
        echo "  -> WARNING: zig download failed; continuing version check."
fi

if [ ! -f "ghostty-$CURRENT_VERSION.tar.gz" ]; then
    echo "  -> Source tarball missing locally; rebuilding..."
    curl -fsSL --retry 3 \
        "https://release.files.ghostty.org/$CURRENT_VERSION/ghostty-$CURRENT_VERSION.tar.gz" \
        -o "ghostty-$CURRENT_VERSION.tar.gz" || \
        echo "  -> WARNING: source tarball rebuild failed; continuing version check."
fi

if [ ! -f "vendor.tar.zst" ]; then
    echo "  -> Vendor cache missing locally; rebuilding..."
    fetch_vendor_cache "$CURRENT_VERSION" || \
        echo "  -> WARNING: vendor cache rebuild failed; continuing version check."
fi

if [ ! -f "ghostty-$CURRENT_VERSION-debian.tar.gz" ]; then
    echo "  -> Wrapper orig missing locally; rebuilding..."
    assemble_wrapper "$CURRENT_VERSION" || \
        echo "  -> WARNING: wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    MIN_ZIG=$(curl -fsSL "https://release.files.ghostty.org/$LATEST_VERSION/ghostty-$LATEST_VERSION.tar.gz" 2>/dev/null \
        | tar -xzO "ghostty-$LATEST_VERSION/build.zig.zon" 2>/dev/null \
        | grep -oP 'minimum_zig_version\s*=\s*"\K[0-9.]+' | head -1)
    if [ -n "$MIN_ZIG" ] && [ "$(printf '%s\n%s\n' "$ZIG_VER" "$MIN_ZIG" | sort -V | tail -1)" != "$ZIG_VER" ]; then
        echo "  -> ⏸️ [HOLD] upstream $LATEST_VERSION requires zig $MIN_ZIG, this recipe pins $ZIG_VER (distro zig). Not bumping."
        exit 0
    fi
    echo "  -> 🚀 [UPDATE] New version detected: $LATEST_VERSION (Current: $CURRENT_VERSION)"

    ARCHIVE_URL="https://release.files.ghostty.org/$LATEST_VERSION/ghostty-$LATEST_VERSION.tar.gz"
    echo "  -> [CHECK] Verifying $ARCHIVE_URL"
    if ! curl --output /dev/null --silent --location --head --fail "$ARCHIVE_URL"; then
        echo "  -> ❌ [ERROR] Release tarball for $LATEST_VERSION is not yet available. Skipping update."
        exit 1
    fi

    fetch_vendor_cache "$LATEST_VERSION" || {
        echo "  -> ❌ [ERROR] Vendor cache rebuild failed; refusing to bump without it."
        exit 1
    }

    curl -fsSL --retry 3 "$ARCHIVE_URL" -o "ghostty-$LATEST_VERSION.tar.gz" || {
        echo "  -> ❌ [ERROR] Source tarball download failed."
        exit 1
    }
    rm -f "ghostty-$CURRENT_VERSION.tar.gz"
    curl -fsSL --retry 3 \
        "https://ziglang.org/download/$ZIG_VER/zig-x86_64-linux-$ZIG_VER.tar.xz" \
        -o "zig-x86_64-linux-$ZIG_VER.tar.xz" || {
        echo "  -> ❌ [ERROR] Zig download failed."
        exit 1
    }
    assemble_wrapper "$LATEST_VERSION" || {
        echo "  -> ❌ [ERROR] Wrapper assembly failed; refusing to bump without it."
        exit 1
    }
    rm -f "ghostty-$CURRENT_VERSION-debian.tar.gz"
    curl -fsSL --retry 3 \
        "https://release.files.ghostty.org/$LATEST_VERSION/ghostty-$LATEST_VERSION.tar.gz.minisig" \
        -o "ghostty-$LATEST_VERSION.tar.gz.minisig" || \
        echo "  -> WARNING: minisig download failed; continuing."
    rm -f "ghostty-$CURRENT_VERSION.tar.gz.minisig"

    sed -i "s/^Version:\s*.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
    sed -i "s/^Release:\s*.*/Release:        0/" "$SPEC_FILE"

    DSC_FILE="ghostty.dsc"
    sed -i "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
    sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: ghostty-$LATEST_VERSION-debian.tar.gz|" "$DSC_FILE"
    DEB_DATE=$(date -R -u)
    DEB_ENTRY="ghostty ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
    if [ -f "debian.changelog" ]; then
        echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
    else
        echo -e "$DEB_ENTRY" > debian.changelog
    fi

    DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
    NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$DATE - $PACKAGER_ADDR\n\n- Update to upstream release $LATEST_VERSION\n\n"

    if [ -f "$CHANGES_FILE" ]; then
        echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
    else
        echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
    fi

    echo "  -> ✅ [DONE] $SPEC_FILE is ready for OBS sync."
else
    echo "  -> ✅ [OK] Ghostty is already on latest ($CURRENT_VERSION)."
fi
