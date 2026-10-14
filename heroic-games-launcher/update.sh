#!/bin/bash
# Package updater
cd "$(dirname "$0")" || exit 1

SPEC_FILE="heroic-games-launcher.spec"
CHANGES_FILE="heroic-games-launcher.changes"
GITHUB_REPO="Heroic-Games-Launcher/HeroicGamesLauncher"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# Latest release
if [ -n "$GITHUB_TOKEN" ]; then
    RESP=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
else
    RESP=$(curl -s "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
fi
LATEST_TAG=$(echo "$RESP" | grep -oP '"tag_name":\s*"\K[^"]+')

if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" == "null" ]; then
    echo "Error: Failed to fetch Heroic version from GitHub. Check API limits or connection."
    exit 1
fi

LATEST_VERSION=$(echo "$LATEST_TAG" | sed 's/^v//;s@-@.@g')
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Orig wrapper helper
build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "heroic-games-launcher-$ver.tar.gz" -C "$tmpd" upstream.deb
    for old in heroic-games-launcher-*.tar heroic-games-launcher-*.tar.gz; do
        [ "$old" = "heroic-games-launcher-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "heroic-games-launcher-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

deb_url_for() {
    echo "https://github.com/$GITHUB_REPO/releases/download/v$1/Heroic-$1-linux-amd64.deb"
}

rpm_url_for() {
    echo "https://github.com/$GITHUB_REPO/releases/download/v$1/Heroic-$1-linux-x86_64.rpm"
}

# Orig guard
if [ ! -f "heroic-games-launcher-$CURRENT_VERSION.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "$(deb_url_for "$CURRENT_VERSION")" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "Already up to date ($CURRENT_VERSION)."
    exit 0
fi

# Dual asset guard
RPM_URL="$(rpm_url_for "$LATEST_VERSION")"
SOURCE_URL="$(deb_url_for "$LATEST_VERSION")"
for url in "$RPM_URL" "$SOURCE_URL"; do
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$url")
    if [ "$HTTP_CODE" != "200" ]; then
        echo "Release asset $url returns HTTP $HTTP_CODE (not 200); not bumping to avoid a broken spec."
        echo "Staying on $CURRENT_VERSION."
        exit 0
    fi
done

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

# Payload guard
GUARD_TMP=$(mktemp -d)
trap 'rm -rf "$GUARD_TMP"' EXIT
curl -fsSL --retry 3 --connect-timeout 60 "$SOURCE_URL" -o "$GUARD_TMP/upstream.deb" \
    || { echo "Payload download failed; spec left untouched."; exit 1; }
(cd "$GUARD_TMP" && ar x upstream.deb data.tar.xz data.tar.zst 2>/dev/null)
if [ -f "$GUARD_TMP/data.tar.xz" ]; then
    tar -xf "$GUARD_TMP/data.tar.xz" -C "$GUARD_TMP"
elif [ -f "$GUARD_TMP/data.tar.zst" ]; then
    tar --zstd -xf "$GUARD_TMP/data.tar.zst" -C "$GUARD_TMP"
else
    echo "Unexpected data.tar compression; spec left untouched."
    exit 1
fi
for ref in opt/Heroic/heroic usr/share/applications/heroic.desktop usr/share/icons/hicolor/256x256/apps/heroic.png; do
    [ -e "$GUARD_TMP/$ref" ] || \
        { echo "HOLD: recipe references $ref but the $LATEST_VERSION payload lacks it; spec left untouched."; exit 1; }
done
trap - EXIT
rm -rf "$GUARD_TMP"

# Spec bump
sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
sed -i -E "s|download/[^/]+/Heroic-[^/]+\.rpm|download/$LATEST_TAG/Heroic-$LATEST_VERSION-linux-x86_64.rpm|g" "$SPEC_FILE"

# Debian sync
build_orig_wrapper "$LATEST_VERSION" "$SOURCE_URL"
DSC_FILE="heroic-games-launcher.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: heroic-games-launcher-$LATEST_VERSION.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="heroic-games-launcher ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

# Changelog
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $LATEST_VERSION-0\n- Update heroic-games-launcher to v$LATEST_VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
