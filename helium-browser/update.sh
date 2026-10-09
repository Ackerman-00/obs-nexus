#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1
# update.sh for Helium Browser (Repackaging Build, OBS edition)

SPEC_FILE="helium-browser.spec"
CHANGES_FILE="helium-browser.changes"
GITHUB_REPO="imputnet/helium-linux"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "🔍 Checking for upstream updates on $GITHUB_REPO..."

# Get latest tag via git ls-remote (no rate limit)
LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$' | sort -V | tail -1)

if [ -z "$LATEST_TAG" ]; then
    echo "  -> ❌ [ERROR] Failed to fetch latest tag."
    exit 1
fi

LATEST_VERSION="$LATEST_TAG"

# Read current version from the spec file
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: fetch the upstream tarball under its
# versioned orig name (content-identical rename, no recompression). The
# tarball is gitignored (*.tar.xz) and rides the OBS sync; per-package
# actions/cache in update-packages.yml keeps it across fresh CI checkouts.
fetch_orig_tarball() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.tar.xz" \
        || { echo "orig tarball download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mv "$tmpd/upstream.tar.xz" "helium-browser-$ver.tar.xz"
    for old in helium-browser-*.tar.xz; do
        [ "$old" = "helium-browser-$ver.tar.xz" ] || rm -f "$old"
    done
    ls -l "helium-browser-$ver.tar.xz"
    trap - EXIT
    rm -rf "$tmpd"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# tarball (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
if [ ! -f "helium-browser-$CURRENT_VERSION.tar.xz" ]; then
    echo "  -> Orig tarball missing locally; rebuilding..."
    fetch_orig_tarball "$CURRENT_VERSION" "https://github.com/$GITHUB_REPO/releases/download/$CURRENT_VERSION/helium-$CURRENT_VERSION-x86_64_linux.tar.xz" || \
        echo "  -> WARNING: orig tarball rebuild failed; continuing version check."
fi

# Compare and update
if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "  -> 🚀 [UPDATE] New version detected: $LATEST_VERSION (Current: $CURRENT_VERSION)"

    # A tag can exist before its release assets do: helium's release workflow
    # uploads the tarballs at the end. Bumping on a tag whose asset is missing
    # produces a spec whose Source0 404s, so every OBS build of that NVR
    # fails. Only bump once the tarball really exists.
    TARBALL_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_VERSION/helium-$LATEST_VERSION-x86_64_linux.tar.xz"
    echo "  -> [CHECK] Verifying $TARBALL_URL"
    if ! curl --output /dev/null --silent --location --head --fail "$TARBALL_URL"; then
        echo "  -> ❌ [ERROR] Linux x86_64 tarball for $LATEST_VERSION is not yet available on GitHub. Skipping update."
        exit 1
    fi

    # 1. Update the Version and Release fields
    sed -i "s/^Version:\s*.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
    sed -i "s/^Release:\s*.*/Release:        0/" "$SPEC_FILE"

    # 1b. Debian_Testing recipe: refresh the orig tarball + metainfo
    # sidecar and keep .dsc/changelog in sync (TARBALL_URL verified 200
    # above; the metainfo sidecar is absent from the tarball).
    fetch_orig_tarball "$LATEST_VERSION" "$TARBALL_URL"
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://raw.githubusercontent.com/$GITHUB_REPO/$LATEST_VERSION/package/net.imput.helium.metainfo.xml" \
        -o "debian.net.imput.helium.metainfo.xml" \
        || echo "WARNING: metainfo sidecar refresh failed; keeping previous copy."
    DSC_FILE="helium-browser.dsc"
    sed -i "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
    sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: helium-browser-$LATEST_VERSION.tar.xz|" "$DSC_FILE"
    DEB_DATE=$(date -R -u)
    DEB_ENTRY="helium-browser ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER  $DEB_DATE\n\n"
    if [ -f "debian.changelog" ]; then
        echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
    else
        echo -e "$DEB_ENTRY" > debian.changelog
    fi

    # 2. Prepend an entry to the OBS changes file
    DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
    NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$DATE - $PACKAGER\n\n- Update to upstream release $LATEST_TAG\n\n"

    if [ -f "$CHANGES_FILE" ]; then
        echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
    else
        echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
    fi

    echo "  -> ✅ [DONE] $SPEC_FILE is ready for OBS sync."
else
    echo "  -> ✅ [OK] Helium is already on latest ($CURRENT_VERSION)."
fi
