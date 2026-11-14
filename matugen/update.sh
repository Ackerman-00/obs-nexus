#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="matugen.spec"
CHANGES_FILE="matugen.changes"
REPO="InioX/matugen"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "🔍 Checking for updates..."

LATEST_TAG=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$REPO/releases/latest")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$REPO/releases/latest")
    fi
    LATEST_TAG=$(echo "$RESP" | jq -r '.tag_name')
    if [ -n "$LATEST_TAG" ] && [ "$LATEST_TAG" != "null" ]; then
        break
    fi
    echo "   Retry $attempt: could not fetch latest tag from GitHub..."
    sleep 5
done
NEW_VER="${LATEST_TAG#v}"

if [ -z "$NEW_VER" ] || [ "$NEW_VER" == "null" ]; then
    echo "❌ Error: Could not fetch latest version."
    exit 1
fi

CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   📂 Current Local: $CURRENT_VER"
echo "   ☁️  Latest Online: $NEW_VER"

build_vendor() {
    local ver="$1" tag="$2"
    echo "📦 Downloading source tarball..."
    rm -f "matugen-$ver.tar.gz"
    curl -fsSL --retry 3 --connect-timeout 20 "https://github.com/$REPO/archive/refs/tags/$tag.tar.gz" -o "matugen-$ver.tar.gz" \
        || { echo "❌ Download failed."; return 1; }
    if ! [ -s "matugen-$ver.tar.gz" ] || ! tar -tzf "matugen-$ver.tar.gz" > /dev/null 2>&1; then
        echo "❌ Downloaded tarball is empty or corrupt."
        return 1
    fi
    echo "📦 Generating Rust vendor tarball..."
    rm -rf "matugen-$ver"
    tar -xzf "matugen-$ver.tar.gz"
    cd "matugen-$ver" || return 1
    echo "⚙️  Vendoring cargo dependencies..."
    if ! cargo vendor > ../cargo_config.tmp 2> /tmp/cargo-vendor.err; then
        cat /tmp/cargo-vendor.err
        echo "❌ cargo vendor failed."
        cd .. && rm -rf "matugen-$ver"
        return 1
    fi
    if ! head -1 ../cargo_config.tmp | grep -q "^\[source"; then
        sed -n '/^\[source/,$p' ../cargo_config.tmp > ../cargo_config
    else
        mv ../cargo_config.tmp ../cargo_config
    fi
    rm -f ../cargo_config.tmp
    echo "🗜️  Compressing vendor tarball..."
    tar -cJf ../vendor.tar.xz vendor
    cd ..
    rm -rf "matugen-$ver"
    if ! [ -s vendor.tar.xz ] || ! [ -s cargo_config ]; then
        echo "❌ Vendor tarball/config missing."
        return 1
    fi
    build_debian_orig "$ver" || return 1
}

build_debian_orig() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d) || return 1
    echo "📦 Assembling combined Debian orig tarball..."
    rm -f matugen-*-debian.tar.gz
    rm -rf "$tmpd/matugen-$ver"
    tar -xzf "matugen-$ver.tar.gz" -C "$tmpd" || { rm -rf "$tmpd"; return 1; }
    tar -xJf vendor.tar.xz -C "$tmpd/matugen-$ver" || { rm -rf "$tmpd"; return 1; }
    cp cargo_config "$tmpd/matugen-$ver/cargo_config" || { rm -rf "$tmpd"; return 1; }
    tar -czf "matugen-$ver-debian.tar.gz" -C "$tmpd" "matugen-$ver" || { rm -rf "$tmpd"; return 1; }
    rm -rf "$tmpd"
    if ! [ -s "matugen-$ver-debian.tar.gz" ]; then
        echo "❌ Combined Debian orig tarball missing."
        return 1
    fi
    tar -tzf "matugen-$ver-debian.tar.gz" | grep -q "matugen-$ver/vendor/ariadne/Cargo.toml" || { echo "❌ Combined orig lacks vendor tree."; return 1; }
    tar -tzf "matugen-$ver-debian.tar.gz" | grep -q "matugen-$ver/cargo_config$" || { echo "❌ Combined orig lacks cargo_config."; return 1; }
}

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    if [ ! -f "matugen-$CURRENT_VER.tar.gz" ] || [ ! -f vendor.tar.xz ] || [ ! -f cargo_config ]; then
        echo "📦 Vendor artifacts missing locally; regenerating..."
        build_vendor "$CURRENT_VER" "v$CURRENT_VER" || \
            echo "⚠️  Vendor regeneration failed; continuing (OBS keeps remote copies until next sync)."
    elif [ ! -f "matugen-$CURRENT_VER-debian.tar.gz" ]; then
        echo "📦 Combined Debian orig missing locally; reassembling..."
        build_debian_orig "$CURRENT_VER" || \
            echo "⚠️  Debian orig reassembly failed; continuing (OBS keeps remote copies until next sync)."
    else
        echo "✅ Package is already up to date."
    fi
    exit 0
fi

echo "🚀 New version found! Updating $SPEC_FILE..."

build_vendor "$NEW_VER" "$LATEST_TAG" \
    || { echo "❌ Vendor build failed; spec left untouched."; exit 1; }

sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"

DSC_FILE="matugen.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: matugen-$NEW_VER-debian.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="matugen ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "📝 Updating changelog..."
FORMATTED_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER_ADDR\n\n- Update matugen to v$NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "🎉 Success! Git files updated to v$NEW_VER and tarballs generated. Ready for OBS sync."
