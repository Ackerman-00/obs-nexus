#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="stoat-desktop.spec"
CHANGES_FILE="stoat-desktop.changes"
GITHUB_REPO="stoatchat/for-desktop"
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

build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.zip" \
        || { echo "orig .zip download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    cp stoat.png "$tmpd/icon.png" \
        || { echo "icon copy failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "stoat-desktop-$ver.tar.gz" -C "$tmpd" upstream.zip icon.png
    for old in stoat-desktop-*.tar stoat-desktop-*.tar.gz; do
        [ "$old" = "stoat-desktop-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "stoat-desktop-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

zip_url_for() {
    echo "https://github.com/$GITHUB_REPO/releases/download/v$1/Stoat-linux-x64-$1.zip"
}

if [ ! -f "stoat-desktop-$CURRENT_VERSION.tar.gz" ]; then
    echo "  -> Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "$(zip_url_for "$CURRENT_VERSION")" || \
        echo "  -> WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "  -> 🚀 [UPDATE] New version detected: $LATEST_VERSION (Current: $CURRENT_VERSION)"

    ZIP_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/Stoat-linux-x64-$LATEST_VERSION.zip"
    echo "  -> [CHECK] Verifying $ZIP_URL"
    if ! curl --output /dev/null --silent --location --head --fail "$ZIP_URL"; then
        echo "  -> ❌ [ERROR] Linux x64 zip for $LATEST_VERSION is not yet available on GitHub. Skipping update."
        exit 1
    fi

    sed -i "s/^Version:\s*.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
    sed -i "s/^Release:\s*.*/Release:        0/" "$SPEC_FILE"

    build_orig_wrapper "$LATEST_VERSION" "$ZIP_URL"
    DSC_FILE="stoat-desktop.dsc"
    sed -i "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
    sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: stoat-desktop-$LATEST_VERSION.tar.gz|" "$DSC_FILE"
    DEB_DATE=$(date -R -u)
    DEB_ENTRY="stoat-desktop ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
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
    echo "  -> ✅ [OK] Stoat Desktop is already on latest ($CURRENT_VERSION)."
fi