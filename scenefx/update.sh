#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="scenefx.spec"
CHANGES_FILE="scenefx.changes"
GITHUB_REPO="wlrfx/scenefx"
PACKAGER="Ackerman-00"
echo "Checking for upstream updates on $GITHUB_REPO..."
LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^[0-9]+\.[0-9]+$' | sort -V | tail -1)
if [ -z "$LATEST_TAG" ]; then
    echo "Error: Could not fetch latest version."
    exit 1
fi
NEW_VER="$LATEST_TAG"
CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')
echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"
fetch_tarball() {
    local ver="$1"
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/refs/tags/$ver.tar.gz" -o "scenefx-$ver.tar.gz" || return 1
    tar -tzf "scenefx-$ver.tar.gz" > /dev/null || return 1
    for old in scenefx-*.tar.gz; do
        [ "$old" = "scenefx-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "scenefx-$ver.tar.gz"
}
if [ ! -f "scenefx-$CURRENT_VER.tar.gz" ]; then
    echo "Tarball missing locally; fetching..."
    fetch_tarball "$CURRENT_VER" || echo "WARNING: fetch failed; continuing."
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
sed -i "s|^%global scen_ver.*|%global scen_ver      $NEW_VER|" "$SPEC_FILE"
fetch_tarball "$NEW_VER" || { echo "Download failed; aborting bump."; exit 1; }
sed -i "s/^Version: .*/Version: $NEW_VER/" scenefx.dsc
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: scenefx-$NEW_VER.tar.gz|" scenefx.dsc
DEB_DATE=$(date -R -u)
DEB_ENTRY="scenefx ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER\n\n- Update scenefx to $NEW_VER\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi
echo "Success! scenefx updated to $NEW_VER. Ready for OBS sync."
