#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="wlroots.spec"
CHANGES_FILE="wlroots.changes"
PACKAGER="Ackerman-00"
SERIES="0.20"
echo "Checking for upstream wlroots $SERIES releases..."
TAGS=$(git ls-remote --tags https://gitlab.freedesktop.org/wlroots/wlroots.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//')
if [ -z "$TAGS" ]; then
    echo "Error: Could not fetch tags."
    exit 1
fi
NEW_VER=$(echo "$TAGS" | grep -E "^$SERIES\.[0-9]+$" | sort -V | tail -1)
if [ -z "$NEW_VER" ]; then
    echo "Error: No $SERIES.x tag found."
    exit 1
fi
CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')
echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"
fetch_tarball() {
    local ver="$1"
    curl -fsSL --retry 3 --connect-timeout 30 "https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/$ver/wlroots-$ver.tar.gz" -o "wlroots-$ver.tar.gz" || return 1
    tar -tzf "wlroots-$ver.tar.gz" > /dev/null || return 1
    for old in wlroots-*.tar.gz; do
        [ "$old" = "wlroots-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "wlroots-$ver.tar.gz"
}
if [ ! -f "wlroots-$CURRENT_VER.tar.gz" ]; then
    echo "Tarball missing locally; fetching..."
    fetch_tarball "$CURRENT_VER" || echo "WARNING: fetch failed; continuing."
fi
if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi
echo "Updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"
sed -i "s|^%global wl_ver.*|%global wl_ver      $NEW_VER|" "$SPEC_FILE"
fetch_tarball "$NEW_VER" || { echo "Download failed; aborting bump."; exit 1; }
sed -i "s/^Version: .*/Version: $NEW_VER/" wlroots.dsc
DEB_DATE=$(date -R -u)
DEB_ENTRY="wlroots ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER\n\n- Update wlroots to $NEW_VER\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi
echo "Success! wlroots updated to $NEW_VER. Ready for OBS sync."
