#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="mangowm.spec"
CHANGES_FILE="mangowm.changes"
GITHUB_REPO="mangowm/mango"
PACKAGER="Ackerman-00"
WLROOTS_VER="0.20.2"
SCEN_VER="0.5"
echo "Checking for upstream updates on $GITHUB_REPO..."
LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
if [ -z "$LATEST_TAG" ]; then
    echo "Error: Could not fetch latest version."
    exit 1
fi
NEW_VER="$LATEST_TAG"
CURRENT_VER=$(grep "^%global mango_ver" "$SPEC_FILE" | awk '{print $3}')
echo "Current: $CURRENT_VER Latest: $NEW_VER"
build_debian_orig() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d)
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/refs/tags/$ver.tar.gz" -o "$tmpd/mango.tar.gz" || return 1
    curl -fsSL --retry 3 --connect-timeout 30 "https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/$WLROOTS_VER/wlroots-$WLROOTS_VER.tar.gz" -o "$tmpd/wlroots.tar.gz" || return 1
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/wlrfx/scenefx/archive/refs/tags/$SCEN_VER.tar.gz" -o "$tmpd/scenefx.tar.gz" || return 1
    mkdir -p "$tmpd/tree"
    tar -xzf "$tmpd/mango.tar.gz" -C "$tmpd/tree" || return 1
    tar -xzf "$tmpd/wlroots.tar.gz" -C "$tmpd/tree" || return 1
    tar -xzf "$tmpd/scenefx.tar.gz" -C "$tmpd/tree" || return 1
    tar -czf "mangowm-$ver-debian.tar.gz" -C "$tmpd/tree" .
    rm -rf "$tmpd"
    ls -l "mangowm-$ver-debian.tar.gz"
}
if [ ! -f "mangowm-$CURRENT_VER-debian.tar.gz" ]; then
    echo "Orig missing; rebuilding..."
    build_debian_orig "$CURRENT_VER" || echo "WARNING: orig rebuild failed."
fi
if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Already up to date."
    exit 0
fi
if ! curl --output /dev/null --silent --location --head --fail "https://github.com/$GITHUB_REPO/archive/refs/tags/$NEW_VER.tar.gz"; then
    echo "HOLD: archive missing."
    exit 0
fi
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"
sed -i "s|^%global mango_ver.*|%global mango_ver      $NEW_VER|" "$SPEC_FILE"
build_debian_orig "$NEW_VER"
sed -i "s/^Version: .*/Version: $NEW_VER/" mangowm.dsc
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: mangowm-$NEW_VER-debian.tar.gz|" mangowm.dsc
DEB_DATE=$(date -R -u)
DEB_ENTRY="mangowm ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $NEW_VER-0\n- Update mangowm to $NEW_VER\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi
echo "Success! mangowm updated to $NEW_VER."
