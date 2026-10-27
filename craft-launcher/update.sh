#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="craft-launcher.spec"
CHANGES_FILE="craft-launcher.changes"
GITHUB_REPO="storytold/craft-launcher"
ART_PREFIX="artcraft-launcher"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=""
LATEST_JSON=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    fi
    LATEST_TAG=$(echo "$RESP" | jq -r '.tag_name')
    if [ -n "$LATEST_TAG" ] && [ "$LATEST_TAG" != "null" ]; then
        LATEST_JSON="$RESP"
        break
    fi
    echo "   Retry $attempt: could not fetch latest tag from GitHub..."
    sleep 5
done
NEW_VER="${LATEST_TAG#v}"

if [ -z "$NEW_VER" ] || [ "$NEW_VER" == "null" ]; then
    echo "Error: Could not fetch latest version."
    exit 1
fi

CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"

RPM_NAME="$ART_PREFIX-$NEW_VER-linux-x86_64.rpm"
DEB_NAME="$ART_PREFIX-$NEW_VER-linux-x86_64.deb"

build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "craft-launcher-$ver.tar.gz" -C "$tmpd" upstream.deb
    for old in craft-launcher-*.tar.gz; do
        [ "$old" = "craft-launcher-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "craft-launcher-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

deb_url_for() {
    echo "https://github.com/$GITHUB_REPO/releases/download/v$1/$ART_PREFIX-$1-linux-x86_64.deb"
}

if [ ! -f "craft-launcher-$CURRENT_VER.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VER" "$(deb_url_for "$CURRENT_VER")" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi

ASSET_NAMES=$(echo "$LATEST_JSON" | jq -r '.assets[]?.name // empty')
for want in "$RPM_NAME" "$DEB_NAME"; do
    if ! echo "$ASSET_NAMES" | grep -qx "$want"; then
        echo "HOLD: $LATEST_TAG has no $want asset. Spec stays on $CURRENT_VER."
        exit 0
    fi
done
echo "RPM + DEB assets present; proceeding."

echo "New version found! Updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"
sed -i "s|^Source0:.*|Source0:        https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$RPM_NAME|" "$SPEC_FILE"

build_orig_wrapper "$NEW_VER" "$(deb_url_for "$NEW_VER")"
DSC_FILE="craft-launcher.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: craft-launcher-$NEW_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="craft-launcher ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "Updating changelog ($CHANGES_FILE)..."
CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- Update craft-launcher to $NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! ArtCraft Launcher updated to v$NEW_VER. Ready for OBS sync."
