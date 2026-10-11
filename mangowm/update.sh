#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="mangowm.spec"
CHANGES_FILE="mangowm.changes"
GITHUB_REPO="mangowm/mango"
PACKAGER="Ackerman-00"
echo "Checking for upstream updates on $GITHUB_REPO..."
LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
if [ -z "$LATEST_TAG" ]; then
    echo "Error: Could not fetch latest version."
    exit 1
fi
NEW_VER="$LATEST_TAG"
CURRENT_VER=$(grep "^%global mango_ver" "$SPEC_FILE" | awk '{print $3}')
WLROOTS_VER=$(grep "^%global wlroots_ver" "$SPEC_FILE" | awk '{print $3}')
SCEN_VER=$(grep "^%global scenefx_ver" "$SPEC_FILE" | awk '{print $3}')
echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"
# ONE source tarball serves BOTH recipes (RPM Source0 + DEB
# Debtransform-Tar): mango + wlroots + scenefx top dirs side by side
# (matugen combined-orig pattern). Gitignored, rides the OBS sync.
build_source_tarball() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d)
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/refs/tags/$ver.tar.gz" -o "$tmpd/mango.tar.gz" || return 1
    curl -fsSL --retry 3 --connect-timeout 30 "https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/$WLROOTS_VER/wlroots-$WLROOTS_VER.tar.gz" -o "$tmpd/wlroots.tar.gz" || return 1
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/wlrfx/scenefx/archive/refs/tags/$SCEN_VER.tar.gz" -o "$tmpd/scenefx.tar.gz" || return 1
    mkdir -p "$tmpd/tree"
    tar -xzf "$tmpd/mango.tar.gz" -C "$tmpd/tree" || return 1
    tar -xzf "$tmpd/wlroots.tar.gz" -C "$tmpd/tree" || return 1
    tar -xzf "$tmpd/scenefx.tar.gz" -C "$tmpd/tree" || return 1
    tar -czf "mangowm-$ver.tar.gz" -C "$tmpd/tree" .
    rm -rf "$tmpd"
    ls -l "mangowm-$ver.tar.gz"
}
if [ ! -f "mangowm-$CURRENT_VER.tar.gz" ]; then
    echo "Source tarball missing locally; rebuilding..."
    build_source_tarball "$CURRENT_VER" || echo "WARNING: rebuild failed; continuing."
fi
if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi
if ! curl --output /dev/null --silent --location --head --fail "https://github.com/$GITHUB_REPO/archive/refs/tags/$NEW_VER.tar.gz"; then
    echo "HOLD: source archive missing. Spec stays on $CURRENT_VER."
    exit 0
fi
echo "Updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"
sed -i "s|^%global mango_ver.*|%global mango_ver      $NEW_VER|" "$SPEC_FILE"
build_source_tarball "$NEW_VER" || { echo "Combined tarball failed; aborting bump."; exit 1; }
sed -i "s/^Version: .*/Version: $NEW_VER/" mangowm.dsc
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: mangowm-$NEW_VER.tar.gz|" mangowm.dsc
DEB_DATE=$(date -R -u)
DEB_ENTRY="mangowm ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER\n\n- Update mangowm to $NEW_VER\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi
echo "Success! mangowm updated to $NEW_VER. Ready for OBS sync."
