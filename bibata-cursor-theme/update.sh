#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="bibata-cursor-theme.spec"
CHANGES_FILE="bibata-cursor-theme.changes"
GITHUB_REPO="ful1e5/Bibata_Cursor"
PACKAGER="Ackerman-00"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v?[0-9]' | sort -V | tail -1)
VERSION=$(echo "$LATEST_TAG" | sed 's/^v//')

if [ -z "$VERSION" ]; then
    echo "Error: Failed to fetch latest tag."
    exit 1
fi

echo "Latest upstream tag: $LATEST_TAG (version: $VERSION)"

CURRENT_VERSION=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: fetch the upstream tarball under its
# versioned orig name (content-identical rename, no recompression). The
# tarball is gitignored (*.tar.xz) and rides the OBS sync; per-package
# actions/cache in update-packages.yml keeps it across fresh CI checkouts.
fetch_orig_tarball() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://github.com/$GITHUB_REPO/releases/download/v$ver/Bibata.tar.xz" \
        -o "$tmpd/upstream.tar.xz" \
        || { echo "orig tarball download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mv "$tmpd/upstream.tar.xz" "bibata-cursor-theme-$ver.tar.xz"
    for old in bibata-cursor-theme-*.tar.xz; do
        [ "$old" = "bibata-cursor-theme-$ver.tar.xz" ] || rm -f "$old"
    done
    ls -l "bibata-cursor-theme-$ver.tar.xz"
    trap - EXIT
    rm -rf "$tmpd"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# tarball (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
if [ ! -f "bibata-cursor-theme-$CURRENT_VERSION.tar.xz" ]; then
    echo "Orig tarball missing locally; rebuilding..."
    fetch_orig_tarball "$CURRENT_VERSION" || \
        echo "WARNING: orig tarball rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$VERSION" ]; then
    echo "Package is already at the latest version ($VERSION). No update needed."
    exit 0
fi

echo "Updating: $CURRENT_VERSION -> $VERSION"

sed -i "s/^Version:.*/Version:        $VERSION/" "$SPEC_FILE"
sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# Debian_Testing recipe: refresh the orig tarball + keep .dsc/changelog
# in sync.
fetch_orig_tarball "$VERSION"
DSC_FILE="bibata-cursor-theme.dsc"
sed -i "s/^Version: .*/Version: $VERSION/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: bibata-cursor-theme-$VERSION.tar.xz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="bibata-cursor-theme ($VERSION-1) unstable; urgency=medium\n\n  * New upstream release $VERSION.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $VERSION-0\n- Update bibata-cursor-theme to v$VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $VERSION."
