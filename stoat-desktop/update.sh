#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1
# update.sh for Stoat Desktop (Repackaging Build, OBS edition)

SPEC_FILE="stoat-desktop.spec"
CHANGES_FILE="stoat-desktop.changes"
GITHUB_REPO="stoatchat/for-desktop"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "🔍 Checking for upstream updates on $GITHUB_REPO..."

# Get latest vX.Y.Z tag via git ls-remote (no rate limit)
LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)

if [ -z "$LATEST_TAG" ]; then
    echo "  -> ❌ [ERROR] Failed to fetch latest tag."
    exit 1
fi

LATEST_VERSION="${LATEST_TAG#v}"

# Read current version from the spec file
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: wrap an upstream .zip into the
# gzip-compressed debtransform orig input (dpkg-source 3.0 (quilt) rejects
# an uncompressed .orig.tar). The wrapper is gitignored (*.tar.gz) and
# rides the OBS sync; per-package actions/cache in update-packages.yml
# keeps it across fresh CI checkouts.
build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.zip" \
        || { echo "orig .zip download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "stoat-desktop-$ver.tar.gz" -C "$tmpd" upstream.zip
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

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# wrapper (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
if [ ! -f "stoat-desktop-$CURRENT_VERSION.tar.gz" ]; then
    echo "  -> Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "$(zip_url_for "$CURRENT_VERSION")" || \
        echo "  -> WARNING: orig wrapper rebuild failed; continuing version check."
fi

# Compare and update
if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "  -> 🚀 [UPDATE] New version detected: $LATEST_VERSION (Current: $CURRENT_VERSION)"

    # A tag can exist before its release assets do: stoat's release workflow
    # uploads the zips at the end. Bumping on a tag whose asset is missing
    # produces a spec whose Source0 404s, so every OBS build of that NVR
    # fails. Only bump once the zip really exists.
    ZIP_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/Stoat-linux-x64-$LATEST_VERSION.zip"
    echo "  -> [CHECK] Verifying $ZIP_URL"
    if ! curl --output /dev/null --silent --location --head --fail "$ZIP_URL"; then
        echo "  -> ❌ [ERROR] Linux x64 zip for $LATEST_VERSION is not yet available on GitHub. Skipping update."
        exit 1
    fi

    # 1. Update the Version and Release fields
    sed -i "s/^Version:\s*.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
    sed -i "s/^Release:\s*.*/Release:        0/" "$SPEC_FILE"

    # 1b. Debian_Testing recipe: refresh the wrapper + keep .dsc/changelog
    # in sync (ZIP_URL verified 200 above).
    build_orig_wrapper "$LATEST_VERSION" "$ZIP_URL"
    DSC_FILE="stoat-desktop.dsc"
    sed -i "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
    sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: stoat-desktop-$LATEST_VERSION.tar.gz|" "$DSC_FILE"
    DEB_DATE=$(date -R -u)
    DEB_ENTRY="stoat-desktop ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER  $DEB_DATE\n\n"
    if [ -f "debian.changelog" ]; then
        echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
    else
        echo -e "$DEB_ENTRY" > debian.changelog
    fi

    # 2. Prepend an entry to the OBS changes file
    DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
    NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$DATE - $PACKAGER\n\n- Update to upstream release $LATEST_VERSION\n\n"

    if [ -f "$CHANGES_FILE" ]; then
        echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
    else
        echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
    fi

    echo "  -> ✅ [DONE] $SPEC_FILE is ready for OBS sync."
else
    echo "  -> ✅ [OK] Stoat Desktop is already on latest ($CURRENT_VERSION)."
fi